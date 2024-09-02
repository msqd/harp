from typing import cast
from unittest.mock import AsyncMock

import pytest
from asgiref.typing import HTTPScope

from harp.asgi import ASGIKernel
from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.controllers import DefaultControllerResolver
from harp.http import HttpRequest, HttpResponse
from harp.utils.bytes import ensure_bytes
from harp.utils.testing.communicators import ASGICommunicator
from harp.views.json import register as register_json_views


async def _create_request(body=None, /, *, method="GET", headers=None):
    receive = AsyncMock(
        return_value={"body": ensure_bytes(body) if body else b""},
    )
    request = HttpRequest(
        HttpRequestAsgiBridge(
            cast(
                HTTPScope,
                {
                    "type": "http",
                    "method": method,
                    **(
                        {"headers": [(ensure_bytes(k), ensure_bytes(v)) for k, v in headers.items()]} if headers else {}
                    ),
                },
            ),
            receive,
        ),
    )
    return request


class ControllerTestFixtureMixin:
    ControllerType = None

    def create_controller(self, *args, **kwargs):
        return self.ControllerType(*args, **kwargs)

    async def call_controller(
        self, controller=None, /, *, body=None, method="GET", headers=None
    ) -> tuple[HttpRequest, HttpResponse]:
        if controller is None:
            controller = self.create_controller()
        request = await _create_request(body or b"", method=method, headers=headers)
        return request, await controller(request)

    @pytest.fixture
    def controller(self, storage):
        raise NotImplementedError('You must implement the "controller" fixture in your test class.')


class ControllerThroughASGIFixtureMixin(ControllerTestFixtureMixin):
    @pytest.fixture
    def kernel(self, controller):
        kernel = ASGIKernel(
            resolver=DefaultControllerResolver(default_controller=controller),
            handle_errors=False,
        )
        register_json_views(kernel.dispatcher)
        return kernel

    @pytest.fixture
    async def client(self, kernel):
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client
