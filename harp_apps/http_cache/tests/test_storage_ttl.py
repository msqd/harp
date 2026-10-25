"""``ttl`` and ``check_ttl_every`` bound how long a cache entry lives in storage.

The janitor does not reclaim cache records: this sweep is the only thing doing it.
"""

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
async def storage(records, clock):
    storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
    yield storage
    await storage.wait_for_sweep()  # a sweep still running would hold the database open


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
        clock.advance(TTL - 3)
        assert len(await storage.get_entries("endpoint/key")) == 1  # a sweep runs here

        clock.advance(5)  # past the ttl, before the next sweep is due

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
        await storage.wait_for_sweep()  # it reclaims bans, and would hold the database open

    async def test_default_ttl_is_24_hours(self, records, clock):
        storage = AsyncStorage(records)
        await store_entry(storage, _request(), _response(), "endpoint/key")

        clock.advance(86400 - 1)
        assert len(await storage.get_entries("endpoint/key")) == 1
        clock.advance(2)
        assert await storage.get_entries("endpoint/key") == []
        await storage.wait_for_sweep()

    async def test_settings_default_to_24_hours(self):
        assert HttpCacheSettings().storage.arguments["ttl"] == 86400


@pytest.mark.asyncio
class TestSweep:
    async def test_expired_entries_nobody_asks_for_are_reclaimed(self, storage, records, clock):
        await store_entry(storage, _request(), _response(), "endpoint/old")
        clock.advance(TTL + 1)
        await store_entry(storage, _request(), _response(), "endpoint/recent")
        await storage.wait_for_sweep()

        assert await records.list_keys() == ["endpoint/recent"]

    async def test_sweep_runs_at_most_once_per_check_ttl_every(self, storage, records, clock, monkeypatch):
        runs = []
        original = records.delete_stored_before

        async def counting(*args, **kwargs):
            runs.append(clock.now)
            return await original(*args, **kwargs)

        monkeypatch.setattr(records, "delete_stored_before", counting)

        for _ in range(5):
            await storage.get_entries("endpoint/key")
        await storage.wait_for_sweep()
        assert runs == []

        clock.advance(CHECK_EVERY + 1)
        for _ in range(5):
            await storage.get_entries("endpoint/key")
        await storage.wait_for_sweep()
        assert len(runs) == 1

        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("endpoint/key")
        await storage.wait_for_sweep()
        assert len(runs) == 2

    async def test_an_entry_freshened_since_it_expired_survives_the_sweep(self, storage, records, clock):
        entry = await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL + 1)
        await storage.update_entry(entry.id, lambda e: e)
        await storage.wait_for_sweep()

        assert await records.list_keys() == ["endpoint/key"]


class GatedRecords(MemoryCacheRecords):
    """Records whose expiry waits until the test lets it go."""

    def __init__(self):
        super().__init__()
        self.release = asyncio.Event()
        self.runs = 0

    async def delete_stored_before(self, *args, **kwargs):
        self.runs += 1
        await self.release.wait()
        return await super().delete_stored_before(*args, **kwargs)


@pytest.mark.asyncio
class TestSweepStaysOffTheRequestPath:
    async def test_a_request_does_not_wait_for_the_sweep(self, clock):
        records = GatedRecords()
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(CHECK_EVERY + 1)

        await asyncio.wait_for(storage.get_entries("endpoint/key"), timeout=1)
        await asyncio.wait_for(store_entry(storage, _request(), _response(), "endpoint/other"), timeout=1)

        records.release.set()
        await storage.wait_for_sweep()

    async def test_only_one_sweep_runs_at_a_time(self, clock):
        records = GatedRecords()
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("endpoint/key")
        await asyncio.sleep(0)
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("endpoint/key")
        await asyncio.sleep(0)

        assert records.runs == 1
        records.release.set()
        await storage.wait_for_sweep()

    async def test_sweep_lets_the_event_loop_run(self, clock):
        records = MemoryCacheRecords()
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
        for i in range(SWEEP_DELETE_BATCH * 3):
            await store_entry(storage, _request(), _response(), f"endpoint/key-{i}")
        clock.advance(TTL + 1)  # everything has expired: the sweep deletes batch after batch
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0)
                ticks += 1

        task = asyncio.create_task(ticker())
        await storage.get_entries("endpoint/absent")  # starts the sweep
        await storage.wait_for_sweep()
        task.cancel()

        assert await records.list_keys() == []
        assert ticks >= 3

    async def test_close_cancels_a_running_sweep(self, clock):
        records = GatedRecords()
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=CHECK_EVERY)
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("endpoint/key")
        await asyncio.sleep(0)

        await storage.close()
        await storage.wait_for_sweep()
