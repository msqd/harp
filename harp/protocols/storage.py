from typing import AsyncIterator, Protocol

from harp.core.models.transactions import Transaction


class IStorage(Protocol):
    def find_transactions(self, *, with_messages=False, filters=None) -> AsyncIterator[Transaction]:
        ...

    async def get_blob(self, blob_id):
        ...
