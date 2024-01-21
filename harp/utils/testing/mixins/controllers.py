from unittest.mock import AsyncMock

import pytest

from harp.core.asgi import ASGIKernel, ASGIRequest, ASGIResponse
from harp.core.asgi.resolvers import ControllerResolver
from harp.core.views.json import register as register_json_views
from harp.utils.bytes import ensure_bytes
from harp.utils.testing.communicators import ASGICommunicator


async def create_asgi_context(body=None, /, *, method="GET", headers=None):
    receive = AsyncMock(
        return_value={"body": ensure_bytes(body) if body else b""},
    )
    send = AsyncMock()
    request = ASGIRequest(
        {
            "type": "http",
            "method": method,
            **({"headers": [(ensure_bytes(k), ensure_bytes(v)) for k, v in headers.items()]} if headers else {}),
        },
        receive,
    )
    response = ASGIResponse(request, send)
    return request, response


class ControllerTestFixtureMixin:
    ControllerType = None

    def create_controller(self, *args, **kwargs):
        return self.ControllerType(*args, **kwargs)

    async def call_controller(self, controller=None, /, *, body=None, method="GET", headers=None):
        if controller is None:
            controller = self.create_controller()
        request, response = await create_asgi_context(body or b"", method=method, headers=headers)
        retval = await controller(request, response)
        return request, response, retval

    @pytest.fixture
    def controller(self, storage):
        raise NotImplementedError('You must implement the "controller" fixture in your test class.')


class ControllerThroughASGIFixtureMixin(ControllerTestFixtureMixin):
    @pytest.fixture
    def kernel(self, controller):
        kernel = ASGIKernel(resolver=ControllerResolver(default_controller=controller), handle_errors=False)
        register_json_views(kernel.dispatcher)
        return kernel

    @pytest.fixture
    async def client(self, kernel):
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client
