"""Security tests: the incoming request path must not redirect the proxy to another origin."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController, ProxyRoutingError
from harp_apps.proxy.settings import Endpoint

# Scheme/host hidden behind a leading slash: urlsplit keeps it in the path, then urljoin
# re-absolutizes it to another origin. These must be refused outright.
SCHEME_BEARING_PATHS = ["/http://evil.com/x", "/https://evil.com/x", "/HTTP://evil.com/x"]

# Paths that urljoin already normalizes back onto the configured upstream (must never escape either).
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
async def test_scheme_bearing_request_path_is_rejected(hostile_path):
    # A path like "/http://evil/" would be re-absolutized to another origin by urljoin; reject it.
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    with pytest.raises(ProxyRoutingError):
        await controller._get_next_url_for(context)


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


async def test_scheme_bearing_path_returns_400_and_is_never_forwarded():
    # End-to-end: a hostile path must yield a 400 and the proxy must never issue any upstream request.
    controller = _controller()
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path="/http://evil.com/x"))
    assert response.status == 400
    controller.forward.assert_not_called()
