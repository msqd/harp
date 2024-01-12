from datetime import datetime
from typing import List, Optional, Protocol, TypedDict


class TransactionsGroupedByTimeBucket(TypedDict):
    datetime: datetime
    count: int
    errors: int
    meanDuration: float


class Storage(Protocol):
    async def find_transactions(self, *, with_messages=False, filters=None, page: int = 1, cursor: str = ""):
        """Find transactions, using optional filters, for example to be displayed in the dashboard."""
        ...

    async def get_transaction(self, id, /):
        """Find a transaction, by id."""
        ...

    async def get_blob(self, blob_id):
        """Retrieve a blob, by id. Blobs are content adressable, although the hash is built on the source data and
        blob filters may be applied to the source data before storage, meaning that the hash may not be re-computable
        once storage is done."""
        ...

    async def get_facet_meta(self, name):
        """Retrieve a facet's metadata, by name."""
        ...

    async def transactions_grouped_by_time_bucket(
        self, *, endpoint=None, time_bucket: Optional[str], start_datetime: Optional[datetime]
    ) -> List[TransactionsGroupedByTimeBucket]:
        ...

    async def set_transaction_flag(self, transaction_id: str, username: str, flag_type: str):
        """Set a flag on a transaction."""
        ...

    async def delete_transaction_flag(self, transaction_id: str, username: str, flag_type: str):
        """Delete a flag on a transaction."""
        ...
