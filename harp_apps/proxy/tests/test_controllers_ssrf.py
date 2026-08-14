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


def _controller():
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com"})
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


async def test_scheme_bearing_path_returns_400_and_is_never_forwarded():
    # End-to-end: a hostile path must yield a 400 and the proxy must never issue any upstream request.
    controller = _controller()
    controller.forward = AsyncMock(side_effect=AssertionError("must not forward a hostile request"))
    response = await controller(HttpRequest(method="GET", path="/http://evil.com/x"))
    assert response.status == 400
    controller.forward.assert_not_called()
