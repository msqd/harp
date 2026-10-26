"""
Tells the event system about the state transitions of a remote.

The remote only offers :meth:`Remote.add_state_observer` and knows nothing of events: this module is the one place that
turns an observed transition into the ``loggable`` :class:`RemoteStateChanged`.
"""

import asyncio

from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.unit_of_work import current_unit_of_work
from harp_apps.proxy.adapters import strip_credentials
from harp_apps.proxy.events import EVENT_REMOTE_STATE_CHANGED, RemoteStateChanged
from harp_apps.proxy.settings.remote import Remote

logger = get_logger(__name__)

#: Strong references to the dispatches in flight (the loop only keeps weak ones).
_dispatching: set[asyncio.Task] = set()


def relay_state_changes(remote: Remote, *, endpoint: str, dispatcher: IAsyncEventDispatcher) -> None:
    """
    Dispatches a :class:`RemoteStateChanged` on ``dispatcher`` for every real transition of ``remote``, ``endpoint``
    being the name of the proxy endpoint it serves.

    A transition made inside a unit of work is not relayed: the unit of work records it, with its actor.
    """

    def on_transition(url: str, old: int, new: int) -> None:
        if current_unit_of_work() is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("A remote changed state outside of an event loop, the event is dropped.")
            return
        event = RemoteStateChanged(endpoint=endpoint, url=strip_credentials(url), old=old, new=new)
        task = loop.create_task(dispatch(event))
        _dispatching.add(task)
        task.add_done_callback(_dispatching.discard)

    async def dispatch(event: RemoteStateChanged) -> None:
        try:
            await dispatcher.adispatch(EVENT_REMOTE_STATE_CHANGED, event)
        except Exception:
            logger.exception("A listener of the remote state change failed.")

    remote.add_state_observer(on_transition)
