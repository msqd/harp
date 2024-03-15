from unittest.mock import AsyncMock

import pytest

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.asgi.kernel import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.http import HttpRequest, HttpResponse
from harp.http.tests.stubs import HttpRequestStubBridge


async def mock_controller(request):
    return HttpResponse("Hello, world!", content_type="text/plain")


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
        controller = AsyncMock(wraps=mock_controller, spec=mock_controller)

        kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
        kernel.started = True  # we do not need to test startup here.

        request = HttpRequest(impl)

        response = await kernel.do_handle_http(request, AsyncMock())
        assert controller.await_count == 1
        assert response.status == 200
        assert response.body == b"Hello, world!"
        assert response.headers == {"content-type": "text/plain"}
