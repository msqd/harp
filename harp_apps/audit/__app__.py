"""
Audit Application

Records the auditable events of the other applications in the commit of their action (ADR-0012). Not loaded by default:
the applications that perform critical actions declare ``audit`` in their dependencies.
"""

from harp import get_logger
from harp.config import Application
from harp.config.events import OnBoundEvent
from harp.services import CannotResolveTypeException
from harp.unit_of_work import ANY_EVENT, TransactionalEventDispatcher
from harp_apps.audit.recorder import AuditRecorder
from harp_apps.audit.retention import AuditRetention
from harp_apps.audit.settings import AuditSettings
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.types import IStorage

logger = get_logger(__name__)


async def on_bound(event: OnBoundEvent):
    event.provider.get(TransactionalEventDispatcher).add_listener(ANY_EVENT, AuditRecorder().write)

    try:
        janitor = event.provider.get(JanitorWorker)
    except CannotResolveTypeException:
        logger.warning("The janitor is not loaded: audit events are never purged.")
        return
    retention = AuditRetention(event.provider.get(IStorage), event.provider.get(AuditSettings))
    janitor.sweeps.append(retention.purge)


application = Application(
    dependencies=["storage"],
    on_bound=on_bound,
    settings_type=AuditSettings,
)
