from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.requests import ASGIRequest
from harp.core.asgi.responders import ASGIResponder


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
    def asgi_responder(self, asgi_request, asgi_send):
        return ASGIResponder(asgi_request, asgi_send)

    @respx.mock
    async def test_basic_get(self, asgi_request, asgi_responder):
        endpoint = respx.get("http://example.com/").mock(return_value=Response(200, content=b"Hello."))

        controller = HttpProxyController("http://example.com/")
        await controller(asgi_request, asgi_responder)

        assert endpoint.called
        assert asgi_responder._response == {
            "status": 200,
            "headers": ((b"x-powered-by", b"harp"),),
            "body": b"Hello.",
        }
