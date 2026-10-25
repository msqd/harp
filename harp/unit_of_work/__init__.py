"""
Two-phase unit of work (see ADR-0012).

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
from typing import Optional, Protocol, TypeVar

from whistle import IAsyncEventDispatcher, IEvent

from harp import get_logger
from harp.event_dispatcher import LoggingAsyncEventDispatcher

logger = get_logger(__name__)

__all__ = [
    "IUnitOfWorkFactory",
    "TransactionalEventDispatcher",
    "UnitOfWork",
    "UnsupportedEventError",
    "auditable",
    "is_auditable",
    "is_loggable",
    "loggable",
]

AUDITABLE = "auditable"
LOGGABLE = "loggable"

_E = TypeVar("_E", bound=type)


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
    return _mark(LOGGABLE, event_id)


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
    """


Compensation = Callable[[], Awaitable[None]]


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
        self._transaction_context: Optional[AbstractAsyncContextManager] = None

    @abstractmethod
    def _transaction(self) -> AbstractAsyncContextManager:
        """Opens the transaction: commits on a clean exit, rolls back on an exception."""

    async def record(self, event: IEvent) -> None:
        """Dispatches an auditable event on the transactional dispatcher, inside the transaction."""
        if not is_auditable(event):
            raise UnsupportedEventError(f"{type(event).__name__} is not marked auditable, it cannot be recorded.")
        await self._transactional.adispatch(event.event_id, event)  # type: ignore[attr-defined]
        self._recorded.append(event)

    async def act(self, action: Callable[[], Awaitable[None]], *, compensation: Optional[Compensation] = None) -> None:
        """Runs an action outside the database; a failure of the action propagates and rolls everything back."""
        await action()
        self._actions.append(compensation)

    async def __aenter__(self) -> "UnitOfWork":
        self._transaction_context = self._transaction()
        await self._transaction_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        assert self._transaction_context is not None
        try:
            suppressed = await self._transaction_context.__aexit__(exc_type, exc, tb)
        except BaseException:
            await self._compensate()
            raise
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
        for event in self._recorded:
            try:
                await self._dispatcher.adispatch(event.event_id, event)  # type: ignore[attr-defined]
            except Exception:
                logger.exception(f"A listener of «{event.event_id}» failed after the commit; the commit stands.")  # type: ignore[attr-defined]


class IUnitOfWorkFactory(Protocol):
    """What an acting application depends on: ``async with factory() as uow``."""

    def __call__(self) -> UnitOfWork: ...
