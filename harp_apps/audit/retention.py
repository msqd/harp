from datetime import UTC, datetime

from sqlalchemy import delete

from harp import get_logger
from harp.sweeps import Sweep, SweepBudget
from harp_apps.audit.models import AuditEvent
from harp_apps.audit.settings import AuditSettings

logger = get_logger(__name__)

SWEEP_NAME = "audit.retention"


class AuditRetention:
    """The only deletion of audit events: rows older than ``audit.retention_days``, declared as a sweep."""

    def __init__(self, storage, settings: AuditSettings):
        self.storage = storage
        self.settings = settings

    def sweep(self) -> Sweep:
        """The sweep to declare: on every pass of the janitor, as the purge is a single bounded delete."""
        return Sweep(name=SWEEP_NAME, interval=None, budget=SweepBudget(), run=self.purge)

    async def purge(self, budget: SweepBudget | None = None) -> int:
        threshold = datetime.now(UTC) - self.settings.retention
        async with self.storage.session_factory() as session:
            result = await session.execute(delete(AuditEvent).where(AuditEvent.occurred_at < threshold))
            await session.commit()
        if result.rowcount:
            logger.debug("🧹 Deleted %d old audit events", result.rowcount)
        return result.rowcount
