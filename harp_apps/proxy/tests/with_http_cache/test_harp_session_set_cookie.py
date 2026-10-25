"""An origin's Set-Cookie for HARP's session cookie never reaches the client.

The cache does not store a response carrying a redacted header such as Set-Cookie, so the second request is fresh too;
the strip must hold either way."""

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.http import HttpRequest
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage


def _cached_client():
    return AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryBlobStorage()),
            policy=SpecificationPolicy(
                cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
            ),
        )
    )


@pytest.mark.parametrize("times", [1, 2], ids=["once", "twice"])
async def test_session_set_cookie_is_stripped_on_repeated_requests(times):
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com/"})
    controller = HttpProxyController(http_client=_cached_client(), remote=endpoint.remote, name="test")
    origin = Response(
        200, content=b"hello", headers=[("cache-control", "max-age=3600"), ("set-cookie", "harp_session=evil; Path=/")]
    )
    with respx.mock:
        respx.get("http://example.com/").mock(return_value=origin)
        for _ in range(times):
            result = await controller(HttpRequest(method="GET", path="/"))
            await result.aread()

    assert "set-cookie" not in {name.lower() for name in result.headers}
