"""Security tests: the incoming request path must not redirect the proxy to another origin."""

import re
from itertools import product
from random import Random
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import pytest
from httpx import URL, AsyncByteStream, AsyncClient, MockTransport, Response

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController, ProxyRoutingError
from harp_apps.proxy.settings import Endpoint

# Scheme/host hidden behind a leading slash: urlsplit keeps it in the path. Appended to the base path,
# it stays a path on the configured origin; it must never be read as another origin.
SCHEME_BEARING_PATHS = ["/http://evil.com/x", "/https://evil.com/x", "/HTTP://evil.com/x"]

# Paths whose scheme/host urlsplit drops, leaving a path on the configured upstream (must never escape either).
NORMALIZED_PATHS = ["http://evil.com/x", "https://evil.com/x", "//evil.com/x", "///evil.com/x"]


# Dot segments that walk above the configured base path. urljoin resolves them, and they land on
# the right origin, so the origin check above cannot see them: they escape the subtree the operator
# chose to expose, not the host.
ESCAPING_PATHS = ["/../../admin", "/./../secret", "/a/../../../etc/passwd", "/.."]

# Dot segments that would resolve back inside the configured base path. Clients normalise them before
# sending, so a request still carrying one is refused like any other: nothing is left to normalise
# between the guard and the wire.
INSIDE_DOT_SEGMENT_PATHS = ["/a/../b", "/a/b/../c", "/a/./b", "/a/."]

# Ordinary paths, forwarded on any endpoint.
INNOCENT_PATHS = ["/api/echo", "/", "/a/b/c"]


def _controller(url="http://example.com"):
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": url})
    return HttpProxyController(http_client=AsyncClient(), remote=endpoint.remote, name=endpoint.settings.name)


@pytest.mark.parametrize("hostile_path", SCHEME_BEARING_PATHS + NORMALIZED_PATHS)
async def test_forwarded_url_never_leaves_configured_origin(hostile_path):
    # Core invariant: whatever the request path, the proxy either refuses it or forwards it to the
    # configured upstream host, never to another origin (SSRF / open-proxy).
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    try:
        _base_url, full_url = await controller._get_next_url_for(context)
    except ProxyRoutingError:
        return  # refused outright: safe
    assert urlsplit(full_url).netloc == "example.com", full_url


@pytest.mark.parametrize("hostile_path", SCHEME_BEARING_PATHS)
async def test_scheme_bearing_request_path_stays_a_path_on_the_configured_origin(hostile_path):
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == f"http://example.com{hostile_path}"


async def test_normal_request_path_is_forwarded_unchanged():
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path="/api/echo"))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == "http://example.com/api/echo"


@pytest.mark.parametrize("base_url", ["http://example.com/api/v1/", "http://example.com/api/v1"])
@pytest.mark.parametrize("hostile_path", ESCAPING_PATHS)
async def test_forwarded_url_never_leaves_configured_base_path(base_url, hostile_path):
    # An endpoint url carrying a path is how an operator exposes one subtree of an upstream rather
    # than the whole of it. Dot segments in the request path must not walk out of that subtree: the
    # origin stays right, so nothing else in the chain would notice.
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("base_url", ["http://example.com", "http://example.com/"])
@pytest.mark.parametrize("path", INNOCENT_PATHS)
async def test_endpoint_exposing_a_whole_origin_forwards_ordinary_paths(base_url, path):
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == f"http://example.com{path}"


@pytest.mark.parametrize("base_url", ["http://example.com", "http://example.com/", "http://example.com/api/v1/"])
@pytest.mark.parametrize("path", ESCAPING_PATHS + INSIDE_DOT_SEGMENT_PATHS)
async def test_dot_segments_are_refused_wherever_they_would_resolve(base_url, path):
    # Changed with #1020: dot segments resolving inside the base path, and any dot segment on an
    # endpoint exposing a whole origin, used to be forwarded. The proxy now refuses them all.
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


async def test_path_escaping_the_base_path_returns_400_and_is_never_forwarded():
    # End-to-end: same refusal as a hostile origin, a 400 and no upstream request at all.
    controller = _controller("http://example.com/api/v1/")
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path="/../../admin"))
    assert response.status == 400
    controller.forward.assert_not_called()


# The upstream may decode before it resolves dot segments, so an encoded dot or separator makes a dot
# segment as much as a literal one does, whatever form the escape is hidden in.
ENCODED_DOT_PATHS = ["/%2e%2e/%2e%2e/admin", "/%2E%2E/admin", "/.%2e/admin", "/%2e./admin", "/a/%2e%2E/%2e%2e/admin"]
ENCODED_SLASH_PATHS = ["/..%2f..%2fadmin", "/..%2F..%2Fadmin", "/a%2f..%2f..%2fadmin"]
BACKSLASH_PATHS = ["/x\\..\\..\\admin", "/..\\admin", "/%2e%2e\\admin"]


@pytest.mark.parametrize("hostile_path", ENCODED_DOT_PATHS)
async def test_encoded_dot_segments_escaping_the_base_path_are_rejected(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("hostile_path", ENCODED_SLASH_PATHS)
async def test_encoded_slashes_hiding_an_escape_are_rejected(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("hostile_path", BACKSLASH_PATHS)
async def test_backslashes_hiding_an_escape_are_rejected(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("path", ["/users/a%2eb", "/search%20term", "/a%2fb", "/x%5cy"])
async def test_encoded_characters_inside_a_segment_are_forwarded_with_raw_bytes(path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == f"http://example.com/api/v1{path}"


@pytest.mark.parametrize("hostile_path", [ENCODED_DOT_PATHS[0], ENCODED_SLASH_PATHS[0], BACKSLASH_PATHS[0]])
async def test_encoded_escape_returns_400_without_forwarding_or_tripping_the_breaker(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    status_before = controller.remote[controller.remote.get_url()].status
    response = await controller(HttpRequest(method="GET", path=hostile_path))
    assert response.status == 400
    controller.forward.assert_not_called()
    base_url = controller.remote.get_url()
    assert controller.remote[base_url].status == status_before


# Encoded "%3f" and "%23" must not be read as the start of a query or fragment and hide what follows.
QUERY_FRAGMENT_ESCAPE_PATHS = [
    "/x%3f/%2e%2e/%2e%2e/admin",
    "/x%23/%2e%2e/%2e%2e/admin",
    "/x%3F/..%2f..%2fadmin",
    "/x%23\\..\\..\\admin",
]


@pytest.mark.parametrize("hostile_path", QUERY_FRAGMENT_ESCAPE_PATHS)
async def test_encoded_query_or_fragment_markers_hiding_an_escape_are_rejected(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("path", ["/user%3A42", "/https%3A%2F%2Fgithub.com%2Ffoo", "/a%3fb%23c"])
async def test_encoded_scheme_or_authority_lookalikes_are_ordinary_segments(path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == f"http://example.com/api/v1{path}"


# Upstreams that merge slashes after decoding see no segment between "//": empty segments hide nothing.
EMPTY_SEGMENT_ESCAPE_PATHS = ["/a%2f%2f..%2f..%2fadmin", "/a%2f/..%2f..%2fadmin", "/a//../../admin"]


@pytest.mark.parametrize("hostile_path", EMPTY_SEGMENT_ESCAPE_PATHS)
async def test_empty_segments_do_not_hide_an_escape(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


@pytest.mark.parametrize("path", ["/a//b", "/users/a%2eb", "/user%3A42", "/a%2f%2fb"])
async def test_empty_segments_inside_ordinary_paths_are_forwarded(path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url.startswith("http://example.com/api/v1/"), full_url


# Control and space bytes in a raw path: URL parsers strip or drop them (urljoin made " /api/..." an
# absolute path), so what is checked and what is forwarded would differ. h2 lets them through in
# ":path"; refuse them.
CONTROL_BYTE_PATHS = [
    "/ /api/v1/%2e%2e/%2e%2e/admin",
    "/\x01/api/v1/%2e%2e/%2e%2e/admin",
    "/\x1f/api/v1/%2e%2e/%2e%2e/admin",
    "/ /api/v1/..%2f..%2fadmin",
    "/ /api/%2e%2e/admin",
    "/a\tb",
    "/a\nb",
    "/a\x7fb",
    "/a b",
]


@pytest.mark.parametrize("base_url", ["http://example.com/api/v1/", "http://example.com/api/v1", "http://example.com"])
@pytest.mark.parametrize("hostile_path", CONTROL_BYTE_PATHS)
async def test_control_or_space_bytes_in_the_raw_path_return_400_and_are_never_forwarded(base_url, hostile_path):
    controller = _controller(base_url)
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path=hostile_path))
    assert response.status == 400
    controller.forward.assert_not_called()


# Escapes that only exist on the way: the path ends up back inside the base path, but an upstream
# resolving segment by segment would leave it in between.
TRANSIENT_ESCAPE_PATHS = ["/../v1/b", "/%2e%2e/v1/b", "/..%2fv1/b", "/a/../../v1/b"]


@pytest.mark.parametrize("hostile_path", TRANSIENT_ESCAPE_PATHS)
async def test_transient_escapes_of_the_base_path_are_rejected(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


# The forwarded URL is the endpoint's base path followed by the raw path, never a re-parse of it: a
# colon in the first segment is not a scheme, and what the guard checks is what goes out.
@pytest.mark.parametrize("base_url", ["http://example.com/api/v1/", "http://example.com"])
@pytest.mark.parametrize("path", ["/user:42", "/urn:isbn:0451450523/a", "/http://evil.com/x", "/a/b:c"])
async def test_raw_path_is_appended_to_the_base_path_byte_for_byte(base_url, path):
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == base_url.rstrip("/") + path


# Rows of #1020: an encoded separator before literal dot segments. httpx splits on "/" only and
# resolves the literal ".." before sending, so these went out above the base path.
ENCODED_SEPARATOR_BEFORE_DOTS = [
    ("http://example.com/api/v1", "/a%2fb/../.."),
    ("http://example.com/api/v1", "/a\\b/../.."),
    ("http://example.com/api/v1/", "/a%2fb%2fc/../../.."),
    ("http://example.com/api/v1/", "/a%2fb/../.."),
]


@pytest.mark.parametrize("base_url, hostile_path", ENCODED_SEPARATOR_BEFORE_DOTS)
async def test_encoded_separator_before_literal_dot_segments_returns_400_and_is_never_forwarded(base_url, hostile_path):
    controller = _controller(base_url)
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path=hostile_path))
    assert response.status == 400
    controller.forward.assert_not_called()


# A dot segment is "." or ".." between any two separators the proxy, the http client or an upstream may
# read as one ("/", "%2f", "%5c", "\\", any case), dots literal or "%2e" in any case and any mix.
DOT_SEGMENT_PATHS = [
    "/.",
    "/..",
    "/./a",
    "/%2e",
    "/%2E",
    "/%2e%2E",
    "/.%2e",
    "/%2E.",
    "/a%2f.",
    "/a%2F..",
    "/a%5c.",
    "/a%5C%2e%2e",
    "/a\\.",
    "/a\\..\\b",
    "/a%2f%2e%2fb",
    "/a%2F.%2e%5Cb",
    "/a/..%2fb",
    "/a/.%5cb",
    "/a/%2e\\b",
]


@pytest.mark.parametrize("base_url", ["http://example.com", "http://example.com/api/v1", "http://example.com/api/v1/"])
@pytest.mark.parametrize("hostile_path", DOT_SEGMENT_PATHS)
async def test_dot_segments_under_any_separator_and_dot_encoding_are_refused(base_url, hostile_path):
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


# Shapes an upstream may read as a dot segment after its own normalisation (#1009): ";" path
# parameters, a second decoding, overlong UTF-8, truncation at NUL, Unicode normalisation.
ALTERNATE_DOT_SEGMENT_PATHS = [
    "/..;/..;/admin",
    "/%2e%2e;/%2e%2e;/admin",
    "/.;x=1/admin",
    "/%252e%252e/%252e%252e/admin",
    "/%25252e%25252e/admin",
    "/%252e%252e%252fadmin",
    "/%c0%ae%c0%ae/admin",
    "/%C0%AE%C0%AE/admin",
    "/%e0%80%ae%e0%80%ae/admin",
    "/%2e%2e%00/x",
    "/..%00/x",
    "/%EF%BC%8E%EF%BC%8E/x",
    "/%EF%BC%8E./x",
]


@pytest.mark.parametrize("base_url", ["http://example.com", "http://example.com/api/v1/"])
@pytest.mark.parametrize("hostile_path", ALTERNATE_DOT_SEGMENT_PATHS)
async def test_alternate_dot_segment_shapes_return_400_and_are_never_forwarded(base_url, hostile_path):
    controller = _controller(base_url)
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path=hostile_path))
    assert response.status == 400
    controller.forward.assert_not_called()


@pytest.mark.parametrize("hostile_path", ["//[x/", "//][@+"])
async def test_request_path_urlsplit_cannot_parse_returns_400(hostile_path):
    controller = _controller("http://example.com/api/v1/")
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path=hostile_path))
    assert response.status == 400
    controller.forward.assert_not_called()


# Dots inside a segment, or a segment that only starts or ends with a dot, are no dot segment.
NOT_DOT_SEGMENT_PATHS = [
    "/.well-known/x",
    "/v1.2/x",
    "/a..b",
    "/...",
    "/.a/b.",
    "/users/a%2eb",
    "/%2e%2e%2e",
    "/user%3A42",
    "/a%2fb",
    "/search%20term",
    "/a%2eb",
    "/%20",
    "/%C3%A9",
    "/page;jsessionid=abc",
    "/a;jsessionid=abc/b",
    "/%2520",
]


@pytest.mark.parametrize("base_url", ["http://example.com", "http://example.com/", "http://example.com/api/v1/"])
@pytest.mark.parametrize("path", NOT_DOT_SEGMENT_PATHS)
async def test_paths_without_dot_segments_are_forwarded_byte_for_byte(base_url, path):
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == base_url.rstrip("/") + path
    assert URL(full_url).raw_path == (urlsplit(base_url).path.rstrip("/") + path).encode()


# Property, on the wire: whatever path comes in, the proxy either answers 400, or httpx sends the base
# path followed by the raw request path, byte for byte, with no dot segment under any separator.
WIRE_BASE_URLS = [
    "http://upstream",
    "http://upstream/",
    "http://upstream/api",
    "http://upstream/api/v1",
    "http://upstream/api/v1/",
]
WIRE_ALPHABET = [
    ".",
    "..",
    "%2e",
    "%2E",
    "%2e%2e",
    ".%2e",
    "%2f",
    "%2F",
    "%5c",
    "\\",
    "/",
    "//",
    "a",
    "b",
    "api",
    "v1",
    "%3f",
    "%23",
    "%3A",
    "[",
    "]",
    "@",
]
WIRE_SEPARATORS = re.compile(r"/|\\|%2f|%5c", re.IGNORECASE)
WIRE_DOT_SEGMENT = re.compile(r"(?:\.|%2e){1,2}", re.IGNORECASE)


def _generated_paths():
    """Every concatenation of up to 2 tokens, then seeded random ones of 3 to 8 tokens."""
    for length in range(1, 3):
        for tokens in product(WIRE_ALPHABET, repeat=length):
            yield "/" + "".join(tokens)
    rng = Random(1020)
    for _ in range(1500):
        yield "/" + "".join(rng.choices(WIRE_ALPHABET, k=rng.randint(3, 8)))


def _has_wire_dot_segment(path):
    return any(WIRE_DOT_SEGMENT.fullmatch(segment) for segment in WIRE_SEPARATORS.split(path))


class _EmptyStream(AsyncByteStream):
    """A streamed body, so the client times the response as a real transport would."""

    async def __aiter__(self):
        yield b""


async def test_what_httpx_sends_stays_under_the_base_path_with_no_dot_segment():
    sent = []

    def upstream(request):
        sent.append(request.url.raw_path.decode("ascii"))
        return Response(200, stream=_EmptyStream())

    for base_url in WIRE_BASE_URLS:
        endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": base_url})
        client = AsyncClient(transport=MockTransport(upstream))
        controller = HttpProxyController(http_client=client, remote=endpoint.remote, name="test", logging=False)
        base_path = urlsplit(base_url).path.rsplit("/", 1)[0] + "/"
        for path in _generated_paths():
            sent.clear()
            response = await controller(HttpRequest(method="GET", path=path))
            if response.status == 400:
                assert not sent, (base_url, path, sent)
                continue
            assert response.status == 200, (base_url, path, response.status)
            (wire,) = sent
            assert wire == base_path + urlsplit(path).path.lstrip("/"), (base_url, path, wire)
            assert not _has_wire_dot_segment(wire), (base_url, path, wire)
