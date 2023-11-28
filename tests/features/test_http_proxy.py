"""
Initial implementation : https://trello.com/c/yCdcY7Og/1-5-http-proxy
"""

import pytest

from harp.testing.base import BaseProxyTest
from harp.testing.network_utils import get_available_network_port


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

    @pytest.fixture
    def proxy(self, test_api):
        factory = self.create_proxy_factory()
        proxy_port = get_available_network_port()
        factory.add(test_api.url, port=proxy_port, name="default")
        return factory.create(default_host="proxy.localhost", default_port=proxy_port)

    @pytest.mark.asyncio
    async def test_missing_startup(self, proxy):
        response = await proxy.asgi_http_get("/echo")
        assert response["status"] == 500
        assert response["body"] == (
            b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never "
            b"went through."
        )
        assert response["headers"] == []

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_basic(self, proxy):
        await proxy.asgi_lifespan_startup()
        response = await proxy.asgi_http_get("/echo")
        assert response["status"] == 200
        assert response["body"] == b"GET /echo"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)
