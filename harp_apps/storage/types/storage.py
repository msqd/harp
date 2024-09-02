from datetime import datetime
from typing import Iterable, Protocol

from harp_apps.storage.types import TransactionsGroupedByTimeBucket


class IStorage(Protocol):
    async def initialize(self):
        """Coroutine function to initialize the instance."""
        ...

    async def finalize(self):
        """Coroutine function to finalize the instance. Should release resources, close files etc... The caller should
        make sure to call finalize on all cases where the instance is not needed anymore to get a clean shutdown.
        """
        ...

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
        *,
        username: str,
    ):
        """Find a transaction, by id."""
        ...

    async def get_facet_meta(self, name):
        """Retrieve a facet's metadata, by name."""
        ...

    async def transactions_grouped_by_time_bucket(
        self, *, endpoint: str | None, time_bucket: str, start_datetime: datetime
    ) -> list[TransactionsGroupedByTimeBucket]: ...

    async def set_user_flag(self, *, transaction_id: str, username: str, flag: int, value=True):
        """Sets or unsets a user flag on a transaction."""
        ...

    async def create_users_once_ready(self, users: Iterable[str]):
        """Create users."""
        ...

    async def get_usage(self):
        """Get storage usage."""
        ...
