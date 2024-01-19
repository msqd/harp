from typing import Generic, TypeVar

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


TResult = TypeVar("TResult")


class Results(Generic[TResult]):
    def __init__(self):
        self.items: list[TResult] = []
        self.meta = {}

    def append(self, item: TResult):
        self.items.append(item)


class Repository:
    def __init__(self, session):
        self.session = session
