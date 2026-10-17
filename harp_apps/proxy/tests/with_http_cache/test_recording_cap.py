"""A response over the proxy's recording cap is sent whole and not stored in the http cache (#911)."""

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.http import HttpRequest
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage


def _cached_client():
    return AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryBlobStorage()),
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )
    )


@pytest.mark.parametrize("body, upstream_calls", [(b"0123", 1), (b"01234", 2)], ids=["at-the-cap", "over-the-cap"])
@respx.mock
async def test_cache_stores_only_a_body_within_the_recording_cap(body, upstream_calls):
    upstream = respx.get("http://example.com/").mock(
        return_value=Response(200, content=body, headers={"cache-control": "max-age=3600"})
    )
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": "http://example.com/"}]}),
        http_client=_cached_client(),
        name="api",
        max_recorded_body_size=4,
    )

    for _ in range(2):
        response = await controller(HttpRequest(method="GET", path="/"))
        assert await response.aread() == body

    assert upstream.call_count == upstream_calls
