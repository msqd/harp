from functools import wraps
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    pass


def contextualize_with_session_if_not_provided(f):
    @wraps(f)
    async def contextualized(self, *args, session=None, **kwargs):
        if session is None:
            async with (session or self.session_factory()) as session:
                return await f(self, *args, session=session, **kwargs)
        return await f(self, *args, session=session, **kwargs)

    return contextualized


TRow = TypeVar("TRow")


class Repository(Generic[TRow]):
    Type: TRow = None

    def __init__(self, session_factory, /):
        self.session_factory = session_factory

    def select(self):
        return select(self.Type)

    @contextualize_with_session_if_not_provided
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

    @contextualize_with_session_if_not_provided
    async def find_one_by_id(self, id: str, /, session, **select_kwargs) -> TRow:
        return await self.find_one({"id": id}, session=session, **select_kwargs)

    @contextualize_with_session_if_not_provided
    async def find_or_create_one(self, values: dict, /, session, defaults=None, **select_kwargs) -> TRow:
        try:
            return await self.find_one(values, session=session, **select_kwargs)
        except NoResultFound:
            return await self.create((defaults or {}) | values, session=session)

    @contextualize_with_session_if_not_provided
    async def create(self, values: dict, /, *, session):
        item = self.Type(**values)
        session.add(item)
        await session.commit()
        return item
