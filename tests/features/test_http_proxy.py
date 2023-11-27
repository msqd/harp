"""
Initial implementation : https://trello.com/c/yCdcY7Og/1-5-http-proxy
"""

import pytest
from asgiref.testing import ApplicationCommunicator
from hypercorn.typing import LifespanScope, LifespanStartupEvent

from harp.testing.base import BaseProxyTest


class TestAsgiProxyWithoutEndpoints(BaseProxyTest):
    @pytest.mark.asyncio
    async def test_asgi_proxy_get_no_endpoint(self):
        proxy = self.factory().create()
        response = await proxy.get("/").get_response()
        assert response["status"] == 404
        assert response["body"] == b"No endpoint found for port 80."
        assert response["headers"] == []


class TestAsgiProxyWithStubApi(BaseProxyTest):
    def factory(self, stub_api_server, *args, **kwargs):
        factory = super().factory(*args, **kwargs)
        factory.add(f"http://{stub_api_server.host}:{stub_api_server.port}", port=stub_api_server.port, name="default")
        return factory

    @pytest.mark.asyncio
    async def test_missing_startup(self, stub_api_server):
        proxy = self.factory(stub_api_server).create()
        response = await proxy.get("/echo", port=stub_api_server.port).get_response()
        assert response["status"] == 500
        assert response["body"] == (
            b"Unhandled server error: Cannot access service provider, the lifespan.startup"
            b" asgi event probably never went through."
        )
        assert response["headers"] == []

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_basic(self, stub_api_server):
        proxy = self.factory(stub_api_server).create()
        com = ApplicationCommunicator(proxy, LifespanScope(type="lifespan", asgi={"version": "2.0"}))
        await com.send_input(LifespanStartupEvent(type="lifespan.startup"))
        await com.wait()
        response = await proxy.get("/echo", port=stub_api_server.port).get_response()
        assert response["status"] == 200
        assert response["body"] == b"GET /echo"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)
