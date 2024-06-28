from datetime import datetime
from typing import Iterable, List, Optional, Protocol, TypedDict

from harp.models import Blob


class TransactionsGroupedByTimeBucket(TypedDict):
    datetime: datetime
    count: int
    errors: int
    meanDuration: float


class Storage(Protocol):
    async def get_transaction_list(
        self,
        *,
        username: str,
        with_messages=False,
        filters=None,
        page: int = 1,
        cursor: str = "",
        text_search: str = "",
    ):
        """Find transactions, using optional filters, for example to be displayed in the dashboard."""
        ...

    async def get_transaction(
        self,
        id: str,
        /,
        *,
        username: str,
    ):
        """Find a transaction, by id."""
        ...

    async def get_facet_meta(self, name):
        """Retrieve a facet's metadata, by name."""
        ...

    async def transactions_grouped_by_time_bucket(
        self,
        *,
        endpoint=None,
        time_bucket: Optional[str],
        start_datetime: Optional[datetime],
    ) -> List[TransactionsGroupedByTimeBucket]: ...

    async def set_user_flag(self, *, transaction_id: str, username: str, flag: int, value=True):
        """Sets or unsets a user flag on a transaction."""
        ...

    async def create_users_once_ready(self, users: Iterable[str]):
        """Create users."""
        ...

    async def get_usage(self):
        """Get storage usage."""
        ...


class BlobStorage(Protocol):
    async def get(self, blob_id: str): ...

    async def put(self, blob: Blob): ...

    async def delete(self, blob_id: str): ...

    async def exists(self, blob_id: str) -> bool: ...


class TransactionsGroupedByTimeBucket(TypedDict):
    datetime: datetime
    count: int
    errors: int
    meanDuration: float
