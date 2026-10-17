import logging

from httpx import AsyncClient

from harp.controllers import ProxyControllerResolver
from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.endpoint import Endpoint


def test_add():
    http_client = AsyncClient()
    endpoint = Endpoint.from_kwargs(settings={"name": "test-endpoint", "port": 8080, "url": "http://example.com/"})
    resolver = ProxyControllerResolver()
    controller = HttpProxyController(http_client=http_client, remote=endpoint.remote, name=endpoint.settings.name)

    resolver.add_endpoint(endpoint, controller=controller)
    assert resolver.endpoints["test-endpoint"] == endpoint
    assert resolver.ports == (8080,)


async def test_resolve():
    http_client = AsyncClient()
    endpoint = Endpoint.from_kwargs(settings={"name": "test-endpoint", "port": 8080, "url": "http://example.com/"})
    resolver = ProxyControllerResolver()
    controller = HttpProxyController(http_client=http_client, remote=endpoint.remote, name=endpoint.settings.name)
    resolver.add_endpoint(endpoint, controller=controller)

    request = HttpRequest(server_port=8080)
    controller = await resolver.resolve(request)
    assert isinstance(controller, HttpProxyController)
    assert controller.name == "test-endpoint"

    request = HttpRequest(server_port=8081)
    controller = await resolver.resolve(request)
    assert controller is resolver.default_controller


def test_resolve_from_endpoint_name():
    http_client = AsyncClient()
    endpoint = Endpoint.from_kwargs(settings={"name": "test-endpoint", "port": 8080, "url": "http://example.com/"})
    resolver = ProxyControllerResolver()
    controller = HttpProxyController(http_client=http_client, remote=endpoint.remote, name=endpoint.settings.name)
    resolver.add_endpoint(endpoint, controller=controller)

    controller = resolver.resolve_by_name("test-endpoint")
    assert isinstance(controller, HttpProxyController)
    assert controller.name == "test-endpoint"

    controller = resolver.resolve_by_name("non-existent")
    assert controller is resolver.default_controller


def test_startup_log_masks_upstream_url_passwords(caplog):
    http_client = AsyncClient()
    endpoint = Endpoint.from_kwargs(
        settings={"name": "secured", "port": 8081, "url": "http://user:p%40ss@upstream.example/"}
    )
    controller = HttpProxyController(http_client=http_client, remote=endpoint.remote, name=endpoint.settings.name)

    with caplog.at_level(logging.INFO):
        ProxyControllerResolver().add_endpoint(endpoint, controller=controller)

    assert "upstream.example" in caplog.text
    assert "p%40ss" not in caplog.text
    assert "user:***@upstream.example" in caplog.text
