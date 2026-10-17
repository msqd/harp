"""The HTTP cache stores and serves under the default storage, the in-memory SQLite database.

A fresh install runs on this storage, and the cache must not lose entries there while other
requests use the database at the same moment. See https://github.com/msqd/harp/issues/995.
"""

import asyncio

import pytest
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable

from harp_apps.http_cache.tests import store_entry
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.storage.engines import SQLAlchemyEngine
from harp_apps.storage.models import Base
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
from harp_apps.storage.settings import StorageSettings

ENTRIES = 20


def _request(i):
    return Request(method="GET", url=f"http://endpoint/resource/{i}", headers=Headers({}))


def _response(i):
    return Response(
        status_code=200,
        headers=Headers({"cache-control": "max-age=300", "content-type": "text/plain"}),
        stream=AnyIterable(f"payload {i}".encode()),
        metadata={},
    )


@pytest.fixture
async def default_engine():
    engine = SQLAlchemyEngine.from_url(StorageSettings().url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_entries_stored_concurrently_are_all_served(default_engine):
    """Concurrent lookups must not undo the writes of concurrent stores."""
    storage = AsyncStorage(SqlBlobStorage(default_engine))

    async def miss():
        for _ in range(ENTRIES):
            await storage.get_entries("absent")

    await asyncio.gather(
        *(store_entry(storage, _request(i), _response(i), f"key-{i}") for i in range(ENTRIES)),
        *(miss() for _ in range(5)),
    )

    served = [len(await storage.get_entries(f"key-{i}")) for i in range(ENTRIES)]
    assert served == [1] * ENTRIES
