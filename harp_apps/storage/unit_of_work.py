"""
SQL implementation of the core unit of work (ADR-0013), on the storage session factory.

Transactional listeners write through :func:`current_session`, so their rows join the commit of the action.
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from whistle import IAsyncEventDispatcher

from harp.unit_of_work import TransactionalEventDispatcher, UnitOfWork
from harp_apps.storage.types import IStorage

_current_session: ContextVar[AsyncSession | None] = ContextVar("harp_storage_unit_of_work_session", default=None)


def current_session() -> AsyncSession:
    """The session of the unit of work running in this context, for transactional listeners and the action itself."""
    session = _current_session.get()
    if session is None:
        raise RuntimeError("No unit of work is running in this context.")
    return session


class SqlUnitOfWork(UnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        transactional: IAsyncEventDispatcher,
        dispatcher: IAsyncEventDispatcher,
    ):
        super().__init__(transactional=transactional, dispatcher=dispatcher)
        self._session_factory = session_factory

    @property
    def session(self) -> AsyncSession:
        return current_session()

    @asynccontextmanager
    async def _transaction(self):
        async with self._session_factory() as session:
            token = _current_session.set(session)
            try:
                try:
                    yield session
                except BaseException:
                    await session.rollback()
                    raise
                await session.commit()
            finally:
                _current_session.reset(token)


class SqlUnitOfWorkFactory:
    """Provided by storage as the core's ``IUnitOfWorkFactory``: ``async with factory() as uow``."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        transactional: IAsyncEventDispatcher,
        dispatcher: IAsyncEventDispatcher,
    ):
        self._session_factory = session_factory
        self._transactional = transactional
        self._dispatcher = dispatcher

    @classmethod
    def from_storage(
        cls, storage: IStorage, transactional: TransactionalEventDispatcher, dispatcher: IAsyncEventDispatcher
    ) -> "SqlUnitOfWorkFactory":
        return cls(storage.session_factory, transactional=transactional, dispatcher=dispatcher)  # type: ignore[attr-defined]

    def __call__(self) -> SqlUnitOfWork:
        return SqlUnitOfWork(self._session_factory, transactional=self._transactional, dispatcher=self._dispatcher)
