from typing import AsyncIterator, Protocol

from harp.core.models.transactions import Transaction


class IStorage(Protocol):
    def find_transactions(self, *, with_messages=False, filters=None) -> AsyncIterator[Transaction]:
        """Find transactions, using optional filters, for example to be displayed in the dashboard."""
        ...

    async def get_blob(self, blob_id):
        """Retrieve a blob, by id. Blobs are content adressable, although the hash is built on the source data and
        blob filters may be applied to the source data before storage, meaning that the hash may not be re-computable
        once storage is done."""
        ...

    async def get_facet_meta(self, name):
        """Retrieve a facet's metadata, by name."""
        ...
