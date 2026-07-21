"""Security tests: the incoming request path must not redirect the proxy to another origin."""

from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint


def _controller():
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com"})
    return HttpProxyController(http_client=AsyncClient(), remote=endpoint.remote, name=endpoint.settings.name)


@pytest.mark.parametrize(
    "hostile_path",
    [
        "http://evil.com/x",
        "https://evil.com/x",
        "//evil.com/x",
        "///evil.com/x",
    ],
)
async def test_hostile_request_path_stays_on_configured_host(hostile_path):
    # A request path carrying a scheme/host must not make the proxy fetch another origin
    # (SSRF / open-proxy). The forwarded URL must remain on the configured upstream host.
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path=hostile_path))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert urlsplit(full_url).netloc == "example.com", full_url


async def test_normal_request_path_is_forwarded_unchanged():
    controller = _controller()
    context = SimpleNamespace(request=HttpRequest(method="GET", path="/api/echo"))
    _base_url, full_url = await controller._get_next_url_for(context)
    assert full_url == "http://example.com/api/echo"
