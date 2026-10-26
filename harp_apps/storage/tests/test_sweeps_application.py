"""The janitor application, loaded with the others: storage declares its sweep, the janitor schedules it."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from harp.config import ConfigurationBuilder
from harp.sweeps import SweepRegistry
from harp_apps.janitor.__app__ import JANITOR_WORKER_TASK
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.models import Transaction
from harp_apps.storage.types import IStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


def builder(**storage) -> ConfigurationBuilder:
    builder = ConfigurationBuilder(use_default_applications=False)
    for app in ("http_client", "proxy", "storage", "janitor"):
        builder.applications.add(app, autoload_dependencies=True)
    builder.add_values({"storage": {"url": "sqlite+aiosqlite:///:memory:", **storage}, "janitor": {"period": 3600}})
    return builder


async def stop_background_loop(system):
    task = system.provider.get(JANITOR_WORKER_TASK)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def sweep_warnings(caplog) -> list[str]:
    return [
        r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and "sweep" in r.getMessage().lower()
    ]


class TestJanitorApplication(StorageTestFixtureMixin):
    async def test_storage_declares_the_transaction_purge_and_the_janitor_schedules_it(self, caplog):
        with caplog.at_level(logging.WARNING):
            system = await builder().abuild_system(validate_dependencies=False)
        try:
            sweeps = system.provider.get(SweepRegistry)
            assert [sweep.name for sweep in sweeps] == [
                "storage.transactions",
                "storage.blobs.orphans",
                "storage.metrics",
            ]
            assert sweeps.unscheduled == []
            assert sweep_warnings(caplog) == []
        finally:
            await system.dispose()

    async def test_the_storage_retention_drives_the_declared_purge(self):
        system = await builder(retention_days=2).abuild_system(validate_dependencies=False)
        try:
            await stop_background_loop(system)  # the in-memory database has one connection, keep it for the test
            storage = system.provider.get(IStorage)
            await self.create_transaction(storage, started_at=datetime.now(UTC) - timedelta(days=3))
            await self.create_transaction(storage, started_at=datetime.now(UTC) - timedelta(days=1))

            worker = system.provider.get(JanitorWorker)
            await worker.run_sweeps()

            async with storage.session_factory() as session:
                assert (await session.execute(select(func.count()).select_from(Transaction))).scalar_one() == 1
            assert worker.sweep_stats["storage.transactions"].items == 1
            assert worker.sweep_stats["storage.metrics"].failures == 0
        finally:
            await system.dispose()

    async def test_without_the_janitor_nothing_is_scheduled_and_startup_names_the_sweep(self, caplog):
        configuration = builder()
        configuration.applications.remove("janitor")
        with caplog.at_level(logging.WARNING):
            system = await configuration.abuild_system(validate_dependencies=False)
        try:
            (message,) = sweep_warnings(caplog)
            assert "storage.transactions" in message
        finally:
            await system.dispose()
