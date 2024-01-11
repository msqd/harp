from unittest.mock import AsyncMock

import pytest
import respx
from httpx import AsyncClient, Response

from harp.apps.proxy.controllers import HttpProxyController
from harp.core.asgi.messages import ASGIRequest, ASGIResponse


class TestHttpProxyController:
    @pytest.fixture
    def asgi_receive(self):
        return AsyncMock(return_value={"body": b""})

    @pytest.fixture
    def asgi_request(self, asgi_receive):
        return ASGIRequest({"method": "GET"}, asgi_receive)

    @pytest.fixture
    def asgi_send(self):
        return AsyncMock()

    @pytest.fixture
    def asgi_response(self, asgi_request, asgi_send):
        return ASGIResponse(asgi_request, asgi_send)

    @respx.mock
    async def test_basic_get(self, asgi_request, asgi_response):
        endpoint = respx.get("http://example.com/").mock(return_value=Response(200, content=b"Hello."))

        controller = HttpProxyController("http://example.com/", http_client=AsyncClient())
        await controller(asgi_request, asgi_response)

        assert endpoint.called
        assert asgi_response.snapshot() == {
            "status": 200,
            "headers": (),
            "body": b"Hello.",
        }
