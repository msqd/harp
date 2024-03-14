from unittest.mock import AsyncMock

import pytest

from harp.asgi import ASGIResponse
from harp.asgi.kernel import ASGIKernel
from harp.asgi.resolvers import ControllerResolver
from harp.http import HttpRequest, HttpRequestAsgiBridge
from harp.http.bridge.stub import HttpRequestStubBridge


async def mock_controller(request, response):
    response.headers["content-type"] = "text/plain"
    await response.start()
    await response.body("Hello, world!")


class TestAsgiKernel:
    @pytest.mark.parametrize(
        "impl",
        [
            HttpRequestStubBridge(),
            HttpRequestAsgiBridge(
                {
                    "asgi": {"version": "3.0"},
                    "type": "http",
                    "http_version": "1.1",
                    "method": "GET",
                    "scheme": "http",
                    "path": "/",
                    "raw_path": b"/",
                    "query_string": b"",
                    "headers": [],
                    "client": (),
                    "server": (),
                },
                AsyncMock(),
            ),
        ],
    )
    async def test_basic_request_handling(self, impl):
        controller = AsyncMock(wraps=mock_controller)

        kernel = ASGIKernel(resolver=ControllerResolver(default_controller=controller))
        kernel.started = True  # we do not need to test startup here.

        request = HttpRequest(impl)

        response = (await kernel.handle_http(request, ASGIResponse(request, AsyncMock()))).snapshot()
        assert controller.await_count == 1
        assert response["status"] == 200
        assert response["body"] == b"Hello, world!"
        assert response["headers"] == ((b"content-type", b"text/plain"),)
