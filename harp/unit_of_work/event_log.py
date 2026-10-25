"""
The event log (ADR-0013): the events declared ``loggable`` are written, one structured line each, to ``harp.events``.

Only a declared event can be listened to, and the Operator can only mute one: an unmarked event is never logged.
"""

from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.config.core import CoreSettings
from harp.unit_of_work import is_loggable, loggable_events

EVENTS_LOGGER = "harp.events"

logger = get_logger(EVENTS_LOGGER)

_SCALARS = (str, int, float, bool, type(None))


def _is_scalar(value) -> bool:
    """A scalar, or a flat list of scalars: nothing nested, where a credential could hide."""
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, _SCALARS) for item in value)
    return isinstance(value, _SCALARS)


def _declared_details(event) -> dict:
    """Default-deny: only the detail fields the event class declares, holding scalars, are logged."""
    declared = getattr(type(event), "details_fields", ())
    details = getattr(event, "details", None) or {}
    return {name: value for name, value in details.items() if name in declared and _is_scalar(value)}


async def log_event(event) -> None:
    """
    Writes one structured line for a ``loggable`` event, best-effort: a line that cannot be built is dropped, and the
    dispatch carries on. The mark is checked again here, so an unmarked event never reaches the log, whatever id it was
    dispatched under.
    """
    if not is_loggable(event):
        return
    try:
        logger.info(
            "event",
            kind="event",
            event_id=event.event_id,
            outcome=getattr(event, "outcome", None),
            details=_declared_details(event),
        )
    except Exception:
        pass


def validate_muted_events(muted: list[str]) -> None:
    unknown = sorted(set(muted) - set(loggable_events()))
    if unknown:
        raise ValueError(
            f"core.muted_events can only name loggable events, not: {', '.join(unknown)}. "
            f"Loggable events: {', '.join(sorted(loggable_events())) or 'none'}."
        )


def attach_event_log(dispatcher: IAsyncEventDispatcher, settings: CoreSettings) -> None:
    """Attaches the event log to every declared loggable event that is not muted. Raises if a muted one is not loggable."""
    validate_muted_events(settings.muted_events)
    for event_id in loggable_events():
        if event_id not in settings.muted_events:
            dispatcher.add_listener(event_id, log_event)
