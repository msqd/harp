"""An origin's Set-Cookie for HARP's session cookie never reaches the client, cached response included."""

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


@pytest.mark.parametrize("times", [1, 2], ids=["fresh", "from-cache"])
async def test_session_set_cookie_is_stripped_whether_fresh_or_cached(times):
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com/"})
    controller = HttpProxyController(http_client=_cached_client(), remote=endpoint.remote, name="test")
    origin = Response(
        200, content=b"hello", headers=[("cache-control", "max-age=3600"), ("set-cookie", "harp_session=evil; Path=/")]
    )
    with respx.mock:
        route = respx.get("http://example.com/").mock(return_value=origin)
        for _ in range(times):
            result = await controller(HttpRequest(method="GET", path="/"))
            await result.aread()

    assert route.call_count == 1 if times == 2 else True
    assert "set-cookie" not in {name.lower() for name in result.headers}
