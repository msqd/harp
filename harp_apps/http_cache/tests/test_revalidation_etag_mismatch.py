"""RFC 9111 §4.3.4: a 304 only freshens stored responses with the same strong ETag, else the cache refetches."""

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport

URL = "http://origin.test/item"


class Origin(httpx.AsyncBaseTransport):
    """Serves ETag "a" first; answers any conditional request with a 304 carrying ETag "b"."""

    def __init__(self):
        self.if_none_match: list[str | None] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        sent = request.headers.get("if-none-match")
        self.if_none_match.append(sent)
        if sent:
            return httpx.Response(304, headers={"etag": '"b"', "cache-control": "max-age=0"})
        first = len(self.if_none_match) == 1
        return httpx.Response(
            200,
            headers={"etag": '"a"' if first else '"b"', "cache-control": "max-age=0"},
            content=b"v1" if first else b"v2",
        )


@pytest.mark.asyncio
async def test_304_with_a_different_strong_etag_leads_to_an_unconditional_refetch(mock_storage):
    origin = Origin()
    policy = SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"]))
    transport = AsyncCacheTransport(next_transport=origin, storage=mock_storage, policy=policy)
    async with httpx.AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS) as client:
        await client.get(URL)
        response = await client.get(URL)

    assert origin.if_none_match == [None, '"a"', None]
    assert response.text == "v2"
    assert response.headers["etag"] == '"b"'
