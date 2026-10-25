from functools import wraps
from typing import Generic, TypeVar

from sqlalchemy import MetaData, delete, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.functions import func


# Every constraint gets a deterministic name, because SQLite batch migrations can only alter what they can name.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def with_session(f):
    """
    Decorates a method to ensure it is called with a sql alchemy session, if it is not, then create one to wrap the
    call.

    :param f:
    :return:
    """

    @wraps(f)
    async def contextualized_with_session(self, *args, session=None, **kwargs):
        if session is None:
            async with session or self.session_factory() as session:
                return await f(self, *args, session=session, **kwargs)
        return await f(self, *args, session=session, **kwargs)

    return contextualized_with_session


TRow = TypeVar("TRow")


class Repository(Generic[TRow]):
    Type: TRow = None

    def __init__(self, session_factory, /):
        self.session_factory = session_factory

    def select(self):
        return select(self.Type)

    def delete(self):
        return delete(self.Type)

    def count(self):
        return select(func.count()).select_from(self.Type)

    def update(self):
        return update(self.Type)

    @with_session
    async def find_one(self, values: dict, /, session, **select_kwargs) -> TRow:
        return (
            (
                await session.execute(
                    self.select(**select_kwargs).where(
                        *(getattr(self.Type, attr) == value for attr, value in values.items())
                    )
                )
            )
            .unique()
            .scalar_one()
        )

    @with_session
    async def find_one_by_id(self, id: str, /, session=None, **select_kwargs) -> TRow:
        return await self.find_one({"id": id}, session=session, **select_kwargs)

    @with_session
    async def find_or_create_one(self, values: dict, /, session, defaults=None, **select_kwargs) -> TRow:
        try:
            return await self.find_one(values, session=session, **select_kwargs)
        except NoResultFound:
            return await self.create((defaults or {}) | values, session=session)

    @with_session
    async def create(self, values: dict, /, *, session):
        item = self.Type(**values)
        session.add(item)
        await session.commit()
        return item
