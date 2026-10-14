"""Security tests: the incoming request path must not redirect the proxy to another origin."""

import re
from itertools import product
from random import Random
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import unquote, urlsplit

import pytest
from httpx import URL, AsyncClient, InvalidURL

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

# Dot segments that resolve back inside the configured base path. These are ordinary requests and
# must keep working.
INNOCENT_PATHS = ["/api/echo", "/", "/a/b/c", "/a/../b", "/a/b/../c"]


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
@pytest.mark.parametrize("path", ESCAPING_PATHS + INNOCENT_PATHS)
async def test_endpoint_exposing_a_whole_origin_forwards_everything(base_url, path):
    # Without a path of its own, the endpoint exposes the whole origin and there is no subtree to
    # escape from. Nothing here should be refused.
    controller = _controller(base_url)
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert urlsplit(full_url).netloc == "example.com", full_url


@pytest.mark.parametrize("path", INNOCENT_PATHS)
async def test_paths_resolving_inside_the_base_path_are_forwarded(path):
    # Dot segments are legitimate as long as they resolve back inside the exposed subtree.
    controller = _controller("http://example.com/api/v1/")
    context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert urlsplit(full_url).path.startswith("/api/v1/"), full_url


async def test_path_escaping_the_base_path_returns_400_and_is_never_forwarded():
    # End-to-end: same refusal as a hostile origin, a 400 and no upstream request at all.
    controller = _controller("http://example.com/api/v1/")
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path="/../../admin"))
    assert response.status == 400
    controller.forward.assert_not_called()


# The upstream may decode before it resolves dot segments, so containment is decided on the decoded
# path (with "\" read as "/"), whatever form the escape is hidden in.
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


# Decoded "%3f" and "%23" must not be read as the start of a query or fragment: the decoded view is
# only ever split into path segments.
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


# Upstreams that merge slashes after decoding see no segment between "//": empty segments add no depth.
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
# resolving segment by segment would leave it in between. Literal and encoded dots get the same answer.
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


# Property: whatever path comes in, an upstream that decodes once, reads "\\" as "/", merges slashes
# and resolves dot segments (RFC 3986 5.2.4) on what was forwarded never lands outside the base path.
PROPERTY_BASE_URLS = [
    "http://upstream",
    "http://upstream/",
    "http://upstream/api",
    "http://upstream/api/v1",
    "http://upstream/api/v1/",
]
PROPERTY_ALPHABET = [
    "",
    ".",
    "..",
    "%2e",
    "%2e%2e",
    "%2f",
    "%5c",
    "\\",
    " ",
    "\x01",
    "a",
    "%3f",
    "%23",
    "%3A",
    "api",
    "v1",
]


def _generated_paths():
    """Every path of up to 3 segments, then seeded random ones of 4 to 7 segments."""
    for length in range(1, 4):
        for segments in product(PROPERTY_ALPHABET, repeat=length):
            yield "/" + "/".join(segments)
    rng = Random(1017)
    for _ in range(3000):
        yield "/" + "/".join(rng.choices(PROPERTY_ALPHABET, k=rng.randint(4, 7)))


def _remove_dot_segments(path):
    """RFC 3986 5.2.4 on an absolute path whose slashes are already merged."""
    segments = path.split("/")[1:]
    output = []
    for index, segment in enumerate(segments):
        is_last = index == len(segments) - 1
        if segment == "..":
            if output:
                output.pop()
        elif segment != ".":
            output.append(segment)
            continue
        if is_last:
            output.append("")
    return "/" + "/".join(output)


def _as_resolved_by_upstream(full_url):
    """The path an upstream decoding once and resolving dot segments serves for the URL we send."""
    path = unquote(URL(full_url).raw_path.decode().split("?", 1)[0]).replace("\\", "/")
    return _remove_dot_segments(re.sub("/+", "/", path))


async def test_no_generated_path_resolves_outside_the_base_path_upstream():
    for base_url in PROPERTY_BASE_URLS:
        controller = _controller(base_url)
        base_path = urlsplit(base_url).path.rsplit("/", 1)[0] + "/"
        for path in _generated_paths():
            context = SimpleNamespace(request=HttpRequest(method="GET", path=path))
            try:
                _base_url, full_url = await controller._get_next_url_for(context)
            except ProxyRoutingError:
                continue
            assert urlsplit(full_url).netloc == "upstream", (base_url, path, full_url)
            try:
                URL(full_url)
            except InvalidURL:
                continue  # the http client refuses to send it
            # httpx drops the trailing slash of a path ending in a literal dot segment ("/api/v1/a/.."
            # goes out as "/api/v1"): that is the base resource itself, not a way out of it.
            resolved = _as_resolved_by_upstream(full_url)
            assert resolved.startswith(base_path) or resolved == base_path.rstrip("/"), (base_url, path, full_url)
