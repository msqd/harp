"""The cache declares its periodic maintenance as sweeps (ADR-0014); the janitor schedules them, the cache runs none."""

import logging
from datetime import timedelta

import pytest
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable

from harp.config import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.sweeps import SweepBudget, SweepRegistry
from harp_apps.http_cache.records import BanMode, EndpointStats, MemoryCacheRecords
from harp_apps.http_cache.settings import ReclamationSettings
from harp_apps.http_cache.storages import MAX_KEY_SIZE, AsyncStorage
from harp_apps.http_cache.tests import store_entry
from harp_apps.http_cache.tests.test_storage_ttl import Clock
from harp_apps.janitor.worker import JanitorWorker

EXPIRY, COUNTERS, RECLAMATION = "http_cache.expiry", "http_cache.counters", "http_cache.reclamation"
TTL = 100


def declared(storage: AsyncStorage) -> dict:
    return {sweep.name: sweep for sweep in storage.sweeps()}


def _request():
    return Request(method="GET", url="endpoint/resource", headers=Headers({}))


def _response():
    return Response(
        status_code=200,
        headers=Headers({"cache-control": "max-age=86400", "content-type": "text/plain"}),
        stream=AnyIterable(b"payload"),
        metadata={},
    )


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("harp_apps.http_cache.storages.time", clock)
    monkeypatch.setattr("harp_apps.http_cache.adapters.time", clock)
    return clock


class TestDeclaration:
    def test_the_cache_declares_expiry_counters_and_reclamation(self):
        storage = AsyncStorage(MemoryCacheRecords(), ttl=TTL)

        assert list(declared(storage)) == [EXPIRY, COUNTERS, RECLAMATION]

    def test_expiry_and_counters_run_every_check_ttl_every_seconds(self):
        sweeps = declared(AsyncStorage(MemoryCacheRecords(), ttl=TTL, check_ttl_every=30))

        assert sweeps[EXPIRY].interval == sweeps[COUNTERS].interval == timedelta(seconds=30)

    def test_without_a_pause_between_checks_they_run_on_every_pass(self):
        sweeps = declared(AsyncStorage(MemoryCacheRecords(), ttl=TTL, check_ttl_every=0))

        assert sweeps[EXPIRY].interval is None

    def test_reclamation_runs_on_every_pass_within_the_rounds_and_entries_of_its_settings(self):
        storage = AsyncStorage(MemoryCacheRecords(), reclamation=ReclamationSettings(rounds=3, entries=50))

        sweep = declared(storage)[RECLAMATION]

        assert (sweep.interval, sweep.budget) == (None, SweepBudget(items=150))

    def test_without_a_ttl_nothing_expires_so_no_expiry_sweep(self):
        assert EXPIRY not in declared(AsyncStorage(MemoryCacheRecords(), ttl=None))


@pytest.mark.asyncio
class TestRun:
    async def test_expiry_deletes_the_entries_older_than_the_ttl_and_counts_them(self, records, clock):
        storage = AsyncStorage(records, ttl=TTL)
        await store_entry(storage, _request(), _response(), "endpoint/old")
        clock.advance(TTL + 1)
        await store_entry(storage, _request(), _response(), "endpoint/recent")

        removed = await declared(storage)[EXPIRY].run(SweepBudget())

        assert (removed, await records.list_keys()) == (1, ["endpoint/recent"])

    async def test_reclamation_retires_the_bans_it_has_covered_and_counts_them(self, records):
        storage = AsyncStorage(records, reclamation=ReclamationSettings(grace=0))
        await store_entry(storage, _request(), _response(), "http://api/users/1")
        await storage.invalidate_prefix("api", "/users", mode=BanMode.HARD)

        handled = await declared(storage)[RECLAMATION].run(SweepBudget())

        assert (handled > 0, await records.bans()) == (True, [])

    async def test_counters_write_the_refusals_counted_since_the_last_run(self, records):
        storage = AsyncStorage(records)
        key = "http://api/" + "x" * MAX_KEY_SIZE
        await store_entry(storage, _request(), _response(), key)

        written = await declared(storage)[COUNTERS].run(SweepBudget())

        assert (written, await records.stats()) == (1, [EndpointStats("api", 0, 0, 1)])

    async def test_the_storage_runs_nothing_by_itself(self, records, clock):
        storage = AsyncStorage(records, ttl=TTL, check_ttl_every=0, reclamation=ReclamationSettings(grace=0))
        await store_entry(storage, _request(), _response(), "endpoint/key")
        clock.advance(TTL + 1)
        await storage.invalidate_prefix("api", "/users", mode=BanMode.HARD)

        await storage.get_entries("endpoint/other")
        await store_entry(storage, _request(), _response(), "endpoint/other")

        assert (await records.list_keys(), len(await records.bans())) == (["endpoint/key", "endpoint/other"], 2)


async def build_system(tmp_path, *applications):
    builder = ConfigurationBuilder()
    builder.applications.remove("janitor")
    builder.add_values({"storage": {"url": f"sqlite+aiosqlite:///{tmp_path}/harp.db"}})
    for application in applications:
        builder.applications.add(application)
    return await SystemBuilder(builder.applications, builder.build()).abuild()


@pytest.mark.asyncio
class TestInASystem:
    async def test_the_janitor_schedules_the_sweeps_of_the_cache(self, tmp_path):
        system = await build_system(tmp_path, "http_cache", "janitor")
        try:
            names = [sweep.name for sweep in system.provider.get(JanitorWorker).sweeps]

            assert {EXPIRY, COUNTERS, RECLAMATION} <= set(names)
        finally:
            await system.dispose()

    async def test_the_sweeps_are_those_of_the_storage_the_cache_serves_from(self, tmp_path):
        system = await build_system(tmp_path, "http_cache")
        try:
            storage = system.provider.get("http_cache.storage")

            assert {sweep.name for sweep in system.provider.get(SweepRegistry)} >= {RECLAMATION}
            assert storage._reclamation == ReclamationSettings()
        finally:
            await system.dispose()

    async def test_without_a_janitor_startup_names_the_sweeps_of_the_cache(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING):
            system = await build_system(tmp_path, "http_cache")
        await system.dispose()

        (message,) = [r.getMessage() for r in caplog.records if "sweep" in r.getMessage().lower()]
        assert all(name in message for name in (EXPIRY, COUNTERS, RECLAMATION))
