import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from harp.applications.proxy import Proxy
from harp.models.proxy_endpoint import DeprecatedOldProxyEndpoint


class AsyncMock(MagicMock):
    def __call__(self, *args, **kwargs):
        f = asyncio.Future()
        f.set_result(super(AsyncMock, self).__call__(*args, **kwargs))
        return f


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_asgi_basics():
    app = Proxy(endpoints={8000: DeprecatedOldProxyEndpoint("http://api.example.com/")})

    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost:8000/foo")
        assert response == "foo"
