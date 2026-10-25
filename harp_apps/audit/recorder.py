from datetime import UTC, datetime

from harp import get_logger
from harp.unit_of_work import current_unit_of_work
from harp.unit_of_work.audit import Actor
from harp_apps.audit.models import AuditEvent
from harp_apps.audit.redact import redact
from harp_apps.storage.unit_of_work import current_session

AUDIT_LOGGER = "harp.audit"

logger = get_logger(AUDIT_LOGGER)


def _fields(event) -> dict:
    actor = getattr(event, "actor", None) or Actor()
    target = getattr(event, "target", None)
    return {
        "action": event.event_id,
        "outcome": getattr(event, "outcome", "succeeded"),
        "actor_account_id": actor.account_id,
        "actor_label": actor.label,
        "actor_via": actor.via,
        "actor_via_id": actor.via_id,
        "actor_client": actor.client,
        "ip": actor.ip,
        "user_agent": actor.user_agent,
        "target_type": target.type if target else None,
        "target_id": None if target is None or target.id is None else str(target.id),
        "target_label": target.label if target else None,
        "details": redact(getattr(event, "details", None) or {}),
    }


class AuditRecorder:
    """
    Transactional listener: writes one row per auditable event, in the session of the unit of work that records it, so
    the row joins the commit of the action. A failure raises and rolls the action back.

    The same fields go to the ``harp.audit`` logger once the transaction is committed.
    """

    async def write(self, event) -> None:
        fields = _fields(event)
        row = AuditEvent(occurred_at=datetime.now(UTC), **fields)
        session = current_session()
        session.add(row)
        await session.flush()

        unit_of_work = current_unit_of_work()
        if unit_of_work is not None:
            unit_of_work.after_commit(lambda: self._log(row, fields))

    async def _log(self, row: AuditEvent, fields: dict) -> None:
        logger.info("audit", kind="audit", id=row.id, occurred_at=row.occurred_at.isoformat(), **fields)
