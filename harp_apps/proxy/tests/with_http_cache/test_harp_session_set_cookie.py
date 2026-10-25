"""An origin's Set-Cookie for HARP's session cookie never reaches the client.

By default the cache does not store a response carrying Set-Cookie (a redacted name); an Operator may opt the name out
of redaction (ADR-0009), and the strip must then hold on a replay from cache too."""

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.http import HttpRequest
from harp.models.redaction import Redaction
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint
from harp_apps.http_cache.records import MemoryCacheRecords


def _cached_client(redaction=None):
    async def extend(request):
        if redaction is not None:
            request.extensions["harp"] = {**request.extensions.get("harp", {}), "redaction": redaction}

    return AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryCacheRecords()),
            policy=SpecificationPolicy(
                cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
            ),
        ),
        event_hooks={"request": [extend]},
    )


async def _get_n_times(client, times):
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com/"})
    controller = HttpProxyController(http_client=client, remote=endpoint.remote, name="test")
    origin = Response(
        200, content=b"hello", headers=[("cache-control", "max-age=3600"), ("set-cookie", "harp_session=evil; Path=/")]
    )
    with respx.mock:
        route = respx.get("http://example.com/").mock(return_value=origin)
        for _ in range(times):
            result = await controller(HttpRequest(method="GET", path="/"))
            await result.aread()
    return route, result


@pytest.mark.parametrize("times", [1, 2], ids=["once", "twice"])
async def test_session_set_cookie_is_stripped_on_repeated_requests(times):
    _, result = await _get_n_times(_cached_client(), times)

    assert "set-cookie" not in {name.lower() for name in result.headers}


async def test_session_set_cookie_is_stripped_from_a_cached_response():
    redaction = Redaction()
    redaction.headers.discard("Set-Cookie")

    route, result = await _get_n_times(_cached_client(redaction), 2)

    assert route.call_count == 1
    assert "set-cookie" not in {name.lower() for name in result.headers}
