"""Where the cache keeps its records depends on the applications that are loaded."""

import pytest
from hishel import AsyncBaseStorage

from harp.config import ConfigurationBuilder
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.records.sql import SqlCacheRecords


async def build(*applications):
    config = ConfigurationBuilder({"applications": applications}, use_default_applications=False)
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
