from unittest.mock import AsyncMock

from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.resolvers import ControllerResolver


async def mock_controller(request, response):
    response.headers["content-type"] = "text/plain"
    await response.start()
    await response.body("Hello, world!")


class TestAsgiKernel:
    async def test_basic_request_handling(self):
        controller = AsyncMock(wraps=mock_controller)
        kernel = ASGIKernel(resolver=ControllerResolver(default_controller=controller))
        kernel.started = True  # we do not need to test startup here.
        receive, send = AsyncMock(), AsyncMock()
        request = ASGIRequest(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "query_string": b"",
                "headers": [],
            },
            receive,
        )

        response = (await kernel.handle(request, send)).snapshot()
        assert controller.await_count == 1
        assert response["status"] == 200
        assert response["body"] == b"Hello, world!"
        assert response["headers"] == ((b"content-type", b"text/plain"),)
