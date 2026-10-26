"""Where the cache keeps its records depends on the applications that are loaded."""

import pytest
from hishel import AsyncBaseStorage

from harp.config import ConfigurationBuilder
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.records.redis import RedisCacheRecords
from harp_apps.http_cache.records.sql import SqlCacheRecords


async def build(*applications, **settings):
    config = ConfigurationBuilder({"applications": applications, **settings}, use_default_applications=False)
    return await config.abuild_system(validate_dependencies=False)


async def test_the_records_are_in_the_process_without_the_storage_application():
    system = await build("http_client", "http_cache")

    assert isinstance(system.provider.get(AsyncBaseStorage)._records, MemoryCacheRecords)


@pytest.mark.parametrize(
    "applications", [("http_client", "http_cache", "storage"), ("storage", "http_client", "http_cache")]
)
async def test_the_records_are_in_the_storage_database_with_the_storage_application(applications):
    system = await build(*applications)

    assert isinstance(system.provider.get(AsyncBaseStorage)._records, SqlCacheRecords)


@pytest.mark.parametrize(
    "applications", [("http_client", "http_cache", "storage"), ("storage", "http_client", "http_cache")]
)
async def test_the_records_are_in_redis_when_redis_is_the_blob_storage(applications, redis_url):
    system = await build(
        *applications,
        storage={"blobs": {"type": "redis"}, "redis": {"url": redis_url}},
        http_cache={"redis": {"prefix": "cache:", "retention": 3600}},
    )

    records = system.provider.get(AsyncBaseStorage)._records

    assert isinstance(records, RedisCacheRecords)
    assert records.client is system.provider.get("storage.redis")
    assert (records.prefix, records.retention) == ("cache:", 3600)


async def test_the_records_stay_in_the_database_with_the_sql_blob_storage():
    system = await build("http_client", "http_cache", "storage", storage={"blobs": {"type": "sql"}})

    assert isinstance(system.provider.get(AsyncBaseStorage)._records, SqlCacheRecords)
