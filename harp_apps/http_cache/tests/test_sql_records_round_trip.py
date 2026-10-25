"""A cacheable response goes through the cache, and the SQL records, of the databases production uses.

PostgreSQL enforces what SQLite does not: column widths, index sizes, collations. The compliance suite runs without the
storage application, so this is the path through the cache and the database that nothing else walks.
"""

import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.http_cache.records.sql import SqlCacheRecords
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport


@parametrize_with_database_urls("postgresql", "mysql")
async def test_cacheable_response_is_stored_in_sql_records(sql_engine):
    """The second request is served from the database, not from the origin."""
    records = SqlCacheRecords(sql_engine)
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=AsyncStorage(records),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET"])),
    )

    async with AsyncClient(transport=transport) as client:
        with respx.mock:
            route = respx.get("http://example.com/cacheable").mock(
                return_value=Response(
                    200,
                    json={"hello": "world"},
                    headers={"Cache-Control": "public, max-age=3600"},
                )
            )

            first = await client.get("http://example.com/cacheable", extensions={"harp": {"endpoint": "test"}})
            assert first.status_code == 200

            second = await client.get("http://example.com/cacheable", extensions={"harp": {"endpoint": "test"}})
            assert second.status_code == 200

    # The second request must not have reached the origin, which is only possible if the first
    # response was actually written to, and read back from, the database.
    assert route.call_count == 1
    assert second.json() == {"hello": "world"}
    assert await records.list_keys() == ["http://test/cacheable"]
