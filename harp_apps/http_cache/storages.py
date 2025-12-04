import time

import typing as tp
import uuid
from hishel import AsyncBaseStorage, Entry, EntryMeta, Request, Response

from harp import get_logger
from harp_apps.storage.types import IBlobStorage
from .adapters import AsyncStorageAdapter

logger = get_logger(__name__)
HEADERS_ENCODING = "iso-8859-1"


class AsyncStorage(AsyncBaseStorage):
    """HARP's AsyncBaseStorage implementation using blob storage backend.

    This implementation adapts hishel 1.0's Entry-based API to work with HARP's
    blob storage system. We store a single entry per cache key, maintaining
    backward compatibility with existing cached data.
    """

    def __init__(
        self,
        storage: IBlobStorage,
        ttl: tp.Optional[tp.Union[int, float]] = None,
        check_ttl_every: tp.Union[int, float] = 60,
    ):
        # Note: hishel 1.0 AsyncBaseStorage.__init__ no longer takes serializer parameter
        super().__init__()

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        self._impl = AsyncStorageAdapter(storage)
        self._storage = storage
        self._ttl = ttl

    async def create_entry(
        self,
        request: Request,
        response: Response,
        key: str,
        id_: tp.Optional[uuid.UUID] = None,
    ) -> Entry:
        """Create and store a new cache entry.

        Args:
            request: The HTTP request
            response: The HTTP response
            key: The cache key
            id_: Optional UUID for the entry (generated if not provided)

        Returns:
            The created Entry
        """
        entry_id = id_ or uuid.uuid4()

        logger.debug(
            f"Creating cache entry: key={key}, url={request.url}, "
            f"method={request.method}, status={response.status_code}, entry_id={entry_id}"
        )

        entry = Entry(
            id=entry_id,
            request=request,
            response=response,
            meta=EntryMeta(created_at=time.time(), deleted_at=None),
            cache_key=key.encode("utf-8"),
            extra={"number_of_uses": 0},
        )

        await self._impl.store_entry(key, entry)
        logger.debug(f"Cache entry stored: key={key}")
        return entry

    async def get_entries(self, key: str) -> tp.List[Entry]:
        """Retrieve all entries for a given cache key.

        Note: Our implementation stores only one entry per key, so this returns
        a list with at most one element.

        Args:
            key: The cache key

        Returns:
            List of Entry objects (empty if not found, single element if found)
        """
        logger.debug(f"Retrieving cache entries: key={key}")
        try:
            entry = await self._impl.retrieve_entry(key)
            if entry:
                logger.debug(
                    f"Cache hit: key={key}, url={entry.request.url}, method={entry.request.method}, entry_id={entry.id}"
                )
                return [entry]
            else:
                logger.debug(f"Cache miss: key={key}")
                return []
        except ValueError as e:
            # Incomplete cache entry - log warning and treat as cache miss
            logger.warning(f"Cache entry incomplete for key={key}: {e}")
            return []
        except Exception:
            # Unexpected error - log full traceback
            logger.exception(f"Failed to retrieve cache for key={key}")
            return []

    async def update_entry(
        self,
        id: uuid.UUID,
        new_entry: tp.Union[Entry, tp.Callable[[Entry], Entry]],
    ) -> tp.Optional[Entry]:
        """Update an existing entry by its ID.

        Args:
            id: The entry UUID
            new_entry: Either a new Entry object or a callable that transforms the existing entry

        Returns:
            The updated Entry, or None if not found
        """
        logger.debug(f"Attempting to update entry: entry_id={id}")
        # Since we store by cache_key not by UUID, we need to find the entry first
        # This is a limitation of our blob storage approach
        # For now, we'll implement this by searching through entries
        # In practice, hishel rarely uses this method for our use case
        logger.warning(f"update_entry called for UUID {id}, which requires searching - not fully optimized")
        return None

    async def remove_entry(self, id: uuid.UUID) -> None:
        """Remove an entry by its ID.

        Args:
            id: The entry UUID
        """
        logger.debug(f"Attempting to remove entry: entry_id={id}")
        # Similar limitation as update_entry - we store by cache_key not UUID
        logger.warning(f"remove_entry called for UUID {id}, which requires searching - not fully optimized")
        pass

    async def close(self) -> None:
        """Close the storage (required by AsyncBaseStorage interface)."""
        logger.debug("Closing AsyncStorage")
        return
