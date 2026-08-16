"""
The blobs table holds two kinds of identifier.

Message blobs are keyed by a sha1 hexdigest, 40 characters. HTTP cache entries are keyed by
hishel, which uses a sha256 hexdigest, 64 characters. Both land in ``blobs.id``.

PostgreSQL and MySQL enforce the declared column width, so a column too narrow for the cache key
rejects the insert and the proxy fails the request instead of degrading to a cache miss. SQLite does
not enforce it, which is why this only shows up on the databases production uses.
"""

import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage


@parametrize_with_database_urls("postgresql", "mysql")
async def test_cacheable_response_is_stored_in_sql_blob_storage(sql_engine):
    """A cacheable response must survive a round trip through SQL blob storage.

    This is the path no gate exercised: the compliance suite runs without the storage application,
    and the storage tests never route a cacheable response through the cache.
    """
    blob_storage = SqlBlobStorage(sql_engine)
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=AsyncStorage(storage=blob_storage),
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

            first = await client.get("http://example.com/cacheable")
            assert first.status_code == 200

            second = await client.get("http://example.com/cacheable")
            assert second.status_code == 200

    # The second request must not have reached the origin, which is only possible if the first
    # response was actually written to, and read back from, the database.
    assert route.call_count == 1


@parametrize_with_database_urls("postgresql", "mysql")
async def test_blob_id_column_accepts_a_sha256_key(sql_engine):
    """The narrow version of the same defect, without hishel in the way.

    Kept separate so a failure points straight at the column rather than at the cache.
    """
    from harp.models import Blob

    blob_storage = SqlBlobStorage(sql_engine)
    sha256_length_id = "a" * 64

    await blob_storage.put(Blob(id=sha256_length_id, data=b"payload", content_type="cache/meta"))

    stored = await blob_storage.get(sha256_length_id)
    assert stored is not None
    assert stored.id == sha256_length_id
    assert stored.data == b"payload"
