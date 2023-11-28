"""
Initial implementation : https://trello.com/c/yCdcY7Og/1-5-http-proxy
"""

import pytest

from harp.testing.base import BaseProxyTest
from harp.testing.http import parametrize_with_http_methods
from harp.utils.network import get_available_network_port


class TestAsgiProxyWithoutEndpoints(BaseProxyTest):
    """
    A proxy without configured endpoint will send back 404 responses.

    """

    @pytest.fixture
    def proxy(self):
        factory = self.create_proxy_factory()
        return factory.create()

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_no_endpoint(self, proxy):
        response = await proxy.asgi_http_get("/")
        assert response["status"] == 404
        assert response["body"] == b"No endpoint found for port 80."
        assert response["headers"] == []


class TestAsgiProxyWithStubApi(BaseProxyTest):
    """
    A proxy with an endpoint configured will forward requests to the api, if it has been started first (see asgi's
    lifespan.startup event).

    """

    @pytest.fixture(scope="function")
    def proxy(self, test_api):
        factory = self.create_proxy_factory()
        proxy_port = get_available_network_port()
        factory.add(test_api.url, port=proxy_port, name="default")
        return factory.create(default_host="proxy.localhost", default_port=proxy_port)

    async def test_missing_startup(self, proxy):
        response = await proxy.asgi_http_get("/echo")
        assert response["status"] == 500
        assert response["body"] == (
            b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never "
            b"went through."
        )
        assert response["headers"] == []

    @parametrize_with_http_methods(include_non_standard=True, exclude=("CONNECT", "HEAD"))
    async def test_asgi_proxy_basic_http_requests(self, proxy, method):
        await proxy.asgi_lifespan_startup()
        response = await proxy.asgi_http(method, "/echo")
        assert response["status"] == 200
        assert response["body"] == method.encode("utf-8") + b" /echo"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    async def test_asgi_proxy_basic_http_head_request(self, proxy):
        await proxy.asgi_lifespan_startup()
        response = await proxy.asgi_http_head("/echo")
        assert response["status"] == 200
        assert response["body"] == b""
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    async def test_asgi_proxy_post_basic(self, proxy):
        await proxy.asgi_lifespan_startup()
        response = await proxy.asgi_http_post("/echo")
        assert response["status"] == 200
        assert response["body"] == b"POST /echo"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)
