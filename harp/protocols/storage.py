from datetime import date
from typing import AsyncIterator, List, Protocol, TypedDict

from harp.core.models.transactions import Transaction


class TransactionsGroupedByDate(TypedDict):
    date: date
    transactions: int
    errors: int
    meanDuration: float


class Storage(Protocol):
    def find_transactions(self, *, with_messages=False, filters=None) -> AsyncIterator[Transaction]:
        ...

    async def get_blob(self, blob_id):
        ...

    async def get_facet_meta(self, name):
        ...

    async def transactions_grouped_by_date(self, *, endpoint=None) -> List[TransactionsGroupedByDate]:
        ...
