"""
Events Application

Writes the events declared ``loggable`` to the ``harp.events`` logger, one structured line each (ADR-0013). Only a
declared event can be listened to, and the Operator can only mute one: an unmarked event is never logged.
"""

from whistle import IAsyncEventDispatcher

from harp.config import Application
from harp.config.events import OnBoundEvent
from harp.unit_of_work import loggable_events
from harp_apps.events.listener import log_event
from harp_apps.events.settings import EventsSettings


def _validate_muted(muted: list[str]) -> None:
    unknown = sorted(set(muted) - set(loggable_events()))
    if unknown:
        raise ValueError(
            f"events.muted can only name loggable events, not: {', '.join(unknown)}. "
            f"Loggable events: {', '.join(sorted(loggable_events())) or 'none'}."
        )


async def on_bound(event: OnBoundEvent):
    settings = event.provider.get(EventsSettings)
    _validate_muted(settings.muted)

    dispatcher = event.provider.get(IAsyncEventDispatcher)
    for event_id in loggable_events():
        if event_id not in settings.muted:
            dispatcher.add_listener(event_id, log_event)


application = Application(
    on_bound=on_bound,
    settings_type=EventsSettings,
)
