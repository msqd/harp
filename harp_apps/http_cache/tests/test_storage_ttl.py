"""``ttl`` bounds how long a cache entry lives in storage: a read does not serve an expired entry, and the
``http_cache.expiry`` sweep (``check_ttl_every``, scheduled by the janitor) deletes the ones nobody asks for."""

import asyncio
from dataclasses import replace

import pytest
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable

from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.settings import HttpCacheSettings
from harp_apps.http_cache.storages import SWEEP_DELETE_BATCH, AsyncStorage
from harp_apps.http_cache.tests import store_entry

TTL = 100
CHECK_EVERY = 10


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("harp_apps.http_cache.storages.time", clock)
    monkeypatch.setattr("harp_apps.http_cache.adapters.time", clock)
    return clock


def _request():
    return Request(method="GET", url="endpoint/resource", headers=Headers({}))


def _response(max_age=86400 * 30):
    return Response(
        status_code=200,
        headers=Headers({"cache-control": f"max-age={max_age}", "content-type": "text/plain"}),
        stream=AnyIterable(b"payload"),
        metadata={},
    )


@pytest.fixture
def storage(records, clock):
    return AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)


@pytest.mark.asyncio
class TestEntryExpiry:
    async def test_entry_within_ttl_is_served(self, storage, clock):
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL - 1)

        assert len(await storage.get_entries("endpoint/key")) == 1

    async def test_entry_older_than_ttl_is_not_served_and_is_deleted(self, storage, records, clock):
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL + 1)

        assert await storage.get_entries("endpoint/key") == []
        assert await records.list_keys() == []

    async def test_expired_entry_is_not_served_between_two_sweeps(self, storage, records, clock):
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL + 2)  # past the ttl, before any sweep ran

        assert await storage.get_entries("endpoint/key") == []
        assert await records.list_keys() == []

    async def test_ttl_is_shorter_than_a_long_max_age(self, storage, clock):
        await store_entry(storage, _request(), _response(max_age=86400 * 365), "endpoint/key")
        clock.advance(TTL + 1)

        assert await storage.get_entries("endpoint/key") == []

    async def test_freshening_an_entry_restarts_its_ttl(self, storage, clock):
        entry = await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL - 10)
        await storage.update_entry(entry.id, lambda e: replace(e))
        clock.advance(TTL - 10)

        assert len(await storage.get_entries("endpoint/key")) == 1

    async def test_without_ttl_nothing_expires(self, records, clock):
        storage = AsyncStorage(records, ttl=None, check_ttl_every=CHECK_EVERY)
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(86400 * 365)

        assert len(await storage.get_entries("endpoint/key")) == 1

    async def test_default_ttl_is_24_hours(self, records, clock):
        storage = AsyncStorage(records)
        await store_entry(storage, _request(), _response(), "endpoint/key")

        clock.advance(86400 - 1)
        assert len(await storage.get_entries("endpoint/key")) == 1
        clock.advance(2)
        assert await storage.get_entries("endpoint/key") == []

    async def test_settings_default_to_24_hours(self):
        assert HttpCacheSettings().storage.arguments["ttl"] == 86400


@pytest.mark.asyncio
class TestSweep:
    async def test_expired_entries_nobody_asks_for_are_reclaimed(self, storage, records, clock):
        await store_entry(storage, _request(), _response(), "endpoint/old")
        clock.advance(TTL + 1)
        await store_entry(storage, _request(), _response(), "endpoint/recent")

        await storage.expire()

        assert await records.list_keys() == ["endpoint/recent"]

    async def test_an_entry_freshened_since_it_expired_survives_the_sweep(self, storage, records, clock):
        entry = await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL + 1)
        await storage.update_entry(entry.id, lambda e: e)

        await storage.expire()

        assert await records.list_keys() == ["endpoint/key"]

    async def test_sweep_lets_the_event_loop_run(self, clock):
        records = MemoryCacheRecords()
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
        for i in range(SWEEP_DELETE_BATCH * 4):
            await store_entry(storage, _request(), _response(), f"endpoint/key-{i}")
        clock.advance(TTL + 1)  # everything has expired: the sweep deletes batch after batch
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0)
                ticks += 1

        task = asyncio.create_task(ticker())
        await storage.expire()
        task.cancel()

        assert await records.list_keys() == []
        assert ticks >= 3
