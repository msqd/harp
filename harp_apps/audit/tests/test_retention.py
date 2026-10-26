from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from harp_apps.audit.models import AuditEvent
from harp_apps.audit.retention import AuditRetention
from harp_apps.audit.settings import AuditSettings
from harp_apps.janitor.settings import JanitorSettings
from harp.sweeps import SweepRegistry
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.sweeps import StorageSweeps
from harp_apps.storage.tests import RETENTION
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


def event(days_ago: float) -> AuditEvent:
    return AuditEvent(
        occurred_at=datetime.now(UTC) - timedelta(days=days_ago),
        action="test.noted",
        outcome="succeeded",
        actor_via="system",
    )


async def count(storage) -> int:
    async with storage.session_factory() as session:
        return (await session.execute(select(func.count()).select_from(AuditEvent))).scalar_one()


def test_retention_is_a_year_by_default():
    assert AuditSettings().retention_days == 365


class TestAuditRetention(StorageTestFixtureMixin):
    async def seed(self, storage, *ages):
        async with storage.session_factory() as session:
            session.add_all(event(age) for age in ages)
            await session.commit()

    async def test_purges_what_is_older_than_the_retention(self, sql_storage):
        await self.seed(sql_storage, 366, 400, 364)

        purged = await AuditRetention(sql_storage, AuditSettings()).purge()

        assert purged == 2
        assert await count(sql_storage) == 1

    async def test_retention_follows_the_setting(self, sql_storage):
        await self.seed(sql_storage, 10, 2)

        await AuditRetention(sql_storage, AuditSettings(retention_days=5)).purge()

        assert await count(sql_storage) == 1

    async def test_the_sweep_is_declared_under_the_audit_name(self, sql_storage):
        sweep = AuditRetention(sql_storage, AuditSettings()).sweep()

        assert sweep.name == "audit.retention"

    async def test_the_janitor_runs_the_sweep_without_touching_transaction_retention(self, sql_storage, blob_storage):
        sweeps = SweepRegistry()
        sweeps.declare(AuditRetention(sql_storage, AuditSettings()).sweep())
        for sweep in StorageSweeps(sql_storage, blob_storage, RETENTION).sweeps():
            sweeps.declare(sweep)
        worker = JanitorWorker(JanitorSettings(), sweeps=sweeps)
        await self.seed(sql_storage, 100, 400)
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - timedelta(days=100))

        await worker.run_sweeps()

        assert await count(sql_storage) == 1  # the 100 days old event is kept, the 400 days old one is gone
        assert worker.sweep_stats["audit.retention"].items == 1
        assert worker.sweep_stats["storage.transactions"].items == 1  # transactions: 60 days
        assert worker.sweep_stats["audit.retention"].failures == 0
