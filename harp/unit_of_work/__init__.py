"""
Two-phase unit of work (see ADR-0013).

The core holds the contract and the transactional dispatcher; it has no persistence. An implementation (storage, for the
database) provides :meth:`UnitOfWork._transaction`.

.. code-block:: python

    async with unit_of_work() as uow:
        ...  # the change
        await uow.record(RoleChanged(...))

Inside the transaction, :meth:`UnitOfWork.record` dispatches the event on the transactional dispatcher, where only
listeners declared transactional are attached: their failure rolls the unit of work back. After the commit, the same
event is dispatched on the main dispatcher, for every other listener: a failure there is logged and undoes nothing.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from contextvars import ContextVar, Token
from typing import Optional, Protocol, TypeVar

from whistle import IAsyncEventDispatcher, IEvent

from harp import get_logger
from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.unit_of_work.audit import is_secret_field

logger = get_logger(__name__)

__all__ = [
    "ANY_EVENT",
    "IUnitOfWorkFactory",
    "TransactionalEventDispatcher",
    "UnitOfWork",
    "UnsupportedEventError",
    "auditable",
    "current_unit_of_work",
    "is_auditable",
    "is_loggable",
    "loggable",
    "loggable_events",
]

#: Event id for a transactional listener that wants every recorded event.
ANY_EVENT = "*"

AUDITABLE = "auditable"
LOGGABLE = "loggable"

_E = TypeVar("_E", bound=type)

_loggable_events: dict[str, type] = {}


def _mark(mark: str, event_id: str) -> Callable[[_E], _E]:
    def decorate(event_type: _E) -> _E:
        event_type.event_id = event_id
        event_type.mark = mark
        return event_type

    return decorate


def auditable(event_id: str) -> Callable[[_E], _E]:
    """Declares an event class as a control-plane action, recorded through :meth:`UnitOfWork.record`."""
    return _mark(AUDITABLE, event_id)


def loggable(event_id: str) -> Callable[[_E], _E]:
    """Declares an event class as worth a structured log line, dispatched on the main dispatcher."""
    mark = _mark(LOGGABLE, event_id)

    def decorate(event_type: _E) -> _E:
        secret = [name for name in getattr(event_type, "details_fields", ()) if is_secret_field(name)]
        if secret:
            raise TypeError(
                f"{event_type.__name__} declares detail fields that look like secrets: {', '.join(secret)}."
            )
        _loggable_events[event_id] = event_type
        return mark(event_type)

    return decorate


def loggable_events() -> dict[str, type]:
    """The event classes declared ``loggable`` so far, by event id: what the event log may be asked to mute."""
    return dict(_loggable_events)


def is_auditable(event: object) -> bool:
    return getattr(event, "mark", None) == AUDITABLE


def is_loggable(event: object) -> bool:
    return getattr(event, "mark", None) == LOGGABLE


class UnsupportedEventError(TypeError):
    """Raised when an event that is not marked ``auditable`` is handed to :meth:`UnitOfWork.record`."""


class TransactionalEventDispatcher(LoggingAsyncEventDispatcher):
    """
    The second dispatcher: listeners attached here run inside the unit of work's transaction. Distinct from the main
    dispatcher, so an ordinary listener cannot end up inside a transaction.

    A listener attached to :data:`ANY_EVENT` receives every event recorded, whatever its id: the audit needs it, as it
    cannot know the ids declared by the other applications.
    """

    def get_listeners(self, event_id: Optional[str] = None, /):
        listeners = super().get_listeners(event_id)
        if event_id is None or event_id == ANY_EVENT:
            return listeners
        return (*listeners, *super().get_listeners(ANY_EVENT))


_open_unit_of_work: ContextVar[Optional["UnitOfWork"]] = ContextVar("harp_open_unit_of_work", default=None)

Compensation = Callable[[], Awaitable[None]]
AfterCommit = Callable[[], Awaitable[None]]


def current_unit_of_work() -> Optional["UnitOfWork"]:
    """The unit of work open in this context, if any (for transactional listeners)."""
    return _open_unit_of_work.get()


class UnitOfWork(ABC):
    """
    One action and the record of it, in one commit.

    Implementations provide the transaction. A rolled back transaction leaves nothing; a commit that fails after an
    action calls that action's compensation, else logs a critical error.
    """

    def __init__(self, *, transactional: IAsyncEventDispatcher, dispatcher: IAsyncEventDispatcher):
        self._transactional = transactional
        self._dispatcher = dispatcher
        self._recorded: list[IEvent] = []
        self._actions: list[Optional[Compensation]] = []
        self._after_commit: list[AfterCommit] = []
        self._transaction_context: Optional[AbstractAsyncContextManager] = None
        self._state = "new"
        self._token: Optional[Token] = None

    def _ensure_open(self) -> None:
        if self._state != "open":
            raise RuntimeError("The unit of work is not open: use it inside `async with`.")

    @abstractmethod
    def _transaction(self) -> AbstractAsyncContextManager:
        """Opens the transaction: commits on a clean exit, rolls back on an exception."""

    async def record(self, event: IEvent) -> None:
        """Dispatches an auditable event on the transactional dispatcher, inside the transaction."""
        self._ensure_open()
        if not is_auditable(event):
            raise UnsupportedEventError(f"{type(event).__name__} is not marked auditable, it cannot be recorded.")
        await self._transactional.adispatch(event.event_id, event)  # type: ignore[attr-defined]
        self._recorded.append(event)

    def after_commit(self, callback: AfterCommit) -> None:
        """Runs ``callback`` once the transaction is committed. A failure is logged and undoes nothing."""
        self._ensure_open()
        self._after_commit.append(callback)

    async def act(self, action: Callable[[], Awaitable[None]], *, compensation: Optional[Compensation] = None) -> None:
        """Runs an action outside the database; a failure of the action propagates and rolls everything back."""
        self._ensure_open()
        await action()
        self._actions.append(compensation)

    async def __aenter__(self) -> "UnitOfWork":
        if self._state != "new":
            raise RuntimeError("A unit of work is single-use: create another one.")
        if _open_unit_of_work.get() is not None:
            raise RuntimeError("Units of work cannot be nested: one action, one commit.")
        self._state = "open"
        self._token = _open_unit_of_work.set(self)
        try:
            self._transaction_context = self._transaction()
            await self._transaction_context.__aenter__()
        except BaseException:
            self._close()
            raise
        return self

    def _close(self) -> None:
        self._state = "closed"
        if self._token is not None:
            _open_unit_of_work.reset(self._token)
            self._token = None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        assert self._transaction_context is not None
        try:
            suppressed = await self._transaction_context.__aexit__(exc_type, exc, tb)
        except BaseException:
            self._close()
            await self._compensate()
            raise
        self._close()
        if exc_type is not None:
            await self._compensate()
            return bool(suppressed)
        await self._dispatch_recorded()
        return False

    async def _compensate(self) -> None:
        for compensation in reversed(self._actions):
            if compensation is None:
                logger.critical("An action was performed, its unit of work did not commit and it has no compensation.")
                continue
            try:
                await compensation()
            except Exception:
                logger.critical("A compensation failed after its unit of work did not commit.", exc_info=True)

    async def _dispatch_recorded(self) -> None:
        for callback in self._after_commit:
            try:
                await callback()
            except Exception:
                logger.exception("An after-commit callback failed; the commit stands.")
        for event in self._recorded:
            try:
                await self._dispatcher.adispatch(event.event_id, event)  # type: ignore[attr-defined]
            except Exception:
                logger.exception(f"A listener of «{event.event_id}» failed after the commit; the commit stands.")  # type: ignore[attr-defined]


class IUnitOfWorkFactory(Protocol):
    """What an acting application depends on: ``async with factory() as uow``."""

    def __call__(self) -> UnitOfWork: ...
