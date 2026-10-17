"""``ttl`` and ``check_ttl_every`` bound how long a cache entry lives in storage.

The janitor never deletes ``cache/meta`` blobs: this sweep is the only thing reclaiming them.
"""

import asyncio
import logging
from dataclasses import replace

import pytest
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable

from harp_apps.http_cache.tests import store_entry
from harp_apps.http_cache.settings import HttpCacheSettings
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage
from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage

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
    return Request(method="GET", url="http://endpoint/resource", headers=Headers({}))


def _response(max_age=86400 * 30):
    return Response(
        status_code=200,
        headers=Headers({"cache-control": f"max-age={max_age}", "content-type": "text/plain"}),
        stream=AnyIterable(b"payload"),
        metadata={},
    )


async def cache_metas(blobs: MemoryBlobStorage):
    return [blob.id async for blob in blobs.iter_blobs("cache/meta")]


@pytest.fixture
def blobs():
    return MemoryBlobStorage()


@pytest.fixture
def storage(blobs, clock):
    return AsyncStorage(blobs, ttl=TTL, check_ttl_every=CHECK_EVERY)


@pytest.mark.asyncio
class TestEntryExpiry:
    async def test_entry_within_ttl_is_served(self, storage, clock):
        await store_entry(storage, _request(), _response(), "key")
        clock.advance(TTL - 1)

        assert len(await storage.get_entries("key")) == 1

    async def test_entry_older_than_ttl_is_not_served_and_is_deleted(self, storage, blobs, clock):
        await store_entry(storage, _request(), _response(), "key")
        clock.advance(TTL + 1)

        assert await storage.get_entries("key") == []
        assert await cache_metas(blobs) == []

    async def test_expired_entry_is_not_served_between_two_sweeps(self, storage, blobs, clock):
        await store_entry(storage, _request(), _response(), "key")
        clock.advance(TTL - 3)
        assert len(await storage.get_entries("key")) == 1  # a sweep runs here

        clock.advance(5)  # past the ttl, before the next sweep is due

        assert await storage.get_entries("key") == []
        assert await cache_metas(blobs) == []

    async def test_ttl_is_shorter_than_a_long_max_age(self, storage, clock):
        await store_entry(storage, _request(), _response(max_age=86400 * 365), "key")
        clock.advance(TTL + 1)

        assert await storage.get_entries("key") == []

    async def test_freshening_an_entry_restarts_its_ttl(self, storage, clock):
        entry = await store_entry(storage, _request(), _response(), "key")
        clock.advance(TTL - 10)
        await storage.update_entry(entry.id, lambda e: replace(e))
        clock.advance(TTL - 10)

        assert len(await storage.get_entries("key")) == 1

    async def test_without_ttl_nothing_expires(self, blobs, clock):
        storage = AsyncStorage(blobs, ttl=None, check_ttl_every=CHECK_EVERY)
        await store_entry(storage, _request(), _response(), "key")
        clock.advance(86400 * 365)

        assert len(await storage.get_entries("key")) == 1

    async def test_default_ttl_is_24_hours(self, blobs, clock):
        storage = AsyncStorage(blobs)
        await store_entry(storage, _request(), _response(), "key")

        clock.advance(86400 - 1)
        assert len(await storage.get_entries("key")) == 1
        clock.advance(2)
        assert await storage.get_entries("key") == []

    async def test_settings_default_to_24_hours(self):
        assert HttpCacheSettings().storage.arguments["ttl"] == 86400


@pytest.mark.asyncio
class TestSweep:
    async def test_expired_entries_nobody_asks_for_are_reclaimed(self, storage, blobs, clock):
        await store_entry(storage, _request(), _response(), "old")
        clock.advance(TTL + 1)
        await store_entry(storage, _request(), _response(), "recent")
        await storage.wait_for_sweep()

        assert await cache_metas(blobs) == ["recent"]

    async def test_sweep_runs_at_most_once_per_check_ttl_every(self, storage, blobs, clock, monkeypatch):
        runs = []
        original = blobs.iter_blobs

        def counting(content_type):
            runs.append(clock.now)
            return original(content_type)

        monkeypatch.setattr(blobs, "iter_blobs", counting)

        for _ in range(5):
            await storage.get_entries("key")
        await storage.wait_for_sweep()
        assert runs == []

        clock.advance(CHECK_EVERY + 1)
        for _ in range(5):
            await storage.get_entries("key")
        await storage.wait_for_sweep()
        assert len(runs) == 1

        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("key")
        await storage.wait_for_sweep()
        assert len(runs) == 2


class TestStartupWarning:
    def test_warns_when_the_blob_storage_cannot_enumerate(self, caplog):
        with caplog.at_level(logging.WARNING):
            AsyncStorage(RedisBlobStorage(client=None), ttl=TTL)

        assert "http_cache.storage" in caplog.text and "ttl" in caplog.text

    def test_no_warning_without_ttl(self, caplog):
        with caplog.at_level(logging.WARNING):
            AsyncStorage(RedisBlobStorage(client=None), ttl=None)

        assert caplog.text == ""

    def test_no_warning_when_the_blob_storage_can_enumerate(self, caplog):
        with caplog.at_level(logging.WARNING):
            AsyncStorage(MemoryBlobStorage(), ttl=TTL)

        assert caplog.text == ""


class GatedBlobs(MemoryBlobStorage):
    """Blob storage whose enumeration waits until the test lets it go."""

    def __init__(self):
        super().__init__()
        self.release = asyncio.Event()

    async def iter_blobs(self, content_type):
        await self.release.wait()
        async for blob in super().iter_blobs(content_type):
            yield blob


@pytest.mark.asyncio
class TestSweepStaysOffTheRequestPath:
    async def test_a_request_does_not_wait_for_the_sweep(self, clock):
        blobs = GatedBlobs()
        storage = AsyncStorage(blobs, ttl=TTL, check_ttl_every=CHECK_EVERY)
        await store_entry(storage, _request(), _response(), "key")
        clock.advance(CHECK_EVERY + 1)

        await asyncio.wait_for(storage.get_entries("key"), timeout=1)
        await asyncio.wait_for(store_entry(storage, _request(), _response(), "other"), timeout=1)

        blobs.release.set()
        await storage.wait_for_sweep()

    async def test_only_one_sweep_runs_at_a_time(self, clock, monkeypatch):
        blobs = GatedBlobs()
        storage = AsyncStorage(blobs, ttl=TTL, check_ttl_every=CHECK_EVERY)
        runs = []
        original = blobs.iter_blobs
        monkeypatch.setattr(blobs, "iter_blobs", lambda ct: runs.append(ct) or original(ct))
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("key")
        await asyncio.sleep(0)
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("key")
        await asyncio.sleep(0)

        assert len(runs) == 1
        blobs.release.set()
        await storage.wait_for_sweep()

    async def test_sweep_lets_the_event_loop_run(self, blobs, clock):
        storage = AsyncStorage(blobs, ttl=TTL, check_ttl_every=CHECK_EVERY)
        for i in range(1000):
            await store_entry(storage, _request(), _response(), f"key-{i}")
        clock.advance(CHECK_EVERY + 1)  # sweep due, nothing expired: only the decoding loop can yield
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0)
                ticks += 1

        task = asyncio.create_task(ticker())
        await storage.get_entries("key-0")
        await storage.wait_for_sweep()
        task.cancel()
        assert ticks >= 10

    async def test_close_cancels_a_running_sweep(self, clock):
        blobs = GatedBlobs()
        storage = AsyncStorage(blobs, ttl=TTL, check_ttl_every=CHECK_EVERY)
        clock.advance(CHECK_EVERY + 1)
        await storage.get_entries("key")
        await asyncio.sleep(0)

        await storage.close()
        await storage.wait_for_sweep()


@pytest.mark.asyncio
class TestSweepDeletes:
    async def test_entry_stored_again_after_collection_survives(self, storage, blobs, clock):
        for i in range(5):
            await store_entry(storage, _request(), _response(), f"k{i}")
        clock.advance(TTL + 1)
        original = blobs.delete_blobs

        async def rewrite_then_delete(expired):
            await store_entry(storage, _request(), _response(), "k3")  # same key, fresh stored_at
            await original(expired)

        blobs.delete_blobs = rewrite_then_delete
        await storage.get_entries("nothing")  # starts the sweep
        await storage.wait_for_sweep()

        assert await cache_metas(blobs) == ["k3"]

    async def test_key_deleted_by_a_read_during_the_sweep_does_not_abort_it(self, storage, blobs, clock):
        for i in range(5):
            await store_entry(storage, _request(), _response(), f"k{i}")
        clock.advance(TTL + 1)
        original = blobs.delete_blobs

        async def read_deletes_then_sweep_deletes(expired):
            await blobs.delete("k1")
            await original(expired)

        blobs.delete_blobs = read_deletes_then_sweep_deletes
        await storage.get_entries("nothing")
        await storage.wait_for_sweep()

        assert await cache_metas(blobs) == []
