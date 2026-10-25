from datetime import UTC, datetime

from harp import get_logger
from harp.unit_of_work import current_unit_of_work
from harp.unit_of_work.audit import Actor
from harp_apps.audit.models import AuditEvent
from harp_apps.storage.unit_of_work import current_session

AUDIT_LOGGER = "harp.audit"

logger = get_logger(AUDIT_LOGGER)


_SCALARS = (str, int, float, bool, type(None))


def _is_scalar(value) -> bool:
    """A scalar, or a flat list of scalars: nothing nested, where a credential could hide."""
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, _SCALARS) for item in value)
    return isinstance(value, _SCALARS)


def _declared_details(event) -> dict:
    """
    Default-deny: only the detail fields the event class declares, holding scalars (or a list of scalars), are kept. The
    others are dropped, and their names (never their values) logged.
    """
    declared = getattr(type(event), "details_fields", ())
    details = getattr(event, "details", None) or {}
    kept = {name: value for name, value in details.items() if name in declared and _is_scalar(value)}
    dropped = sorted(str(name) for name in details if name not in kept)
    if dropped:
        logger.warning("Undeclared or non-scalar audit details dropped.", event_id=event.event_id, dropped=dropped)
    return kept


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
        "details": _declared_details(event),
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
