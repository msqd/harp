import time

import typing as tp
import uuid
from collections import OrderedDict
from hishel import AsyncBaseStorage, Entry, EntryMeta, Request, Response

from harp import get_logger
from harp.http.utils import parse_cache_control
from harp_apps.storage.types import IBlobStorage
from .adapters import AsyncStorageAdapter

logger = get_logger(__name__)
HEADERS_ENCODING = "iso-8859-1"


def has_explicit_freshness(response: Response) -> bool:
    """Whether the origin stated how long its response stays fresh.

    Mirrors the first three rules of RFC 9111 §4.2.1 (``s-maxage``, ``max-age``, ``Expires``)
    and deliberately stops before the fourth, which is the ``Last-Modified`` heuristic.
    """
    cache_control = parse_cache_control(response.headers.get("cache-control"))
    return cache_control.s_maxage is not None or cache_control.max_age is not None or "expires" in response.headers


# How many recently seen entry ids keep a route back to their cache key.
#
# The window an id has to survive is a single request cycle, not the lifetime of the entry:
# hishel only ever calls `update_entry` or `remove_entry` with an id the state machine got from
# `get_entries` (or `create_entry`) earlier in that same cycle, in this same process, and
# `http_cache.storage` is a singleton service. So this only has to exceed the number of cache
# lookups a process has in flight at one moment, never the number of entries it has stored.
#
# 8192 is several orders of magnitude above the in-flight concurrency one HARP process reaches,
# and costs a few hundred kilobytes. Lowering it trades that memory for the risk that a 304
# freshens nothing under load, which is the defect this index exists to fix.
KEY_INDEX_SIZE = 8192


class AsyncStorage(AsyncBaseStorage):
    """HARP's AsyncBaseStorage implementation using blob storage backend.

    This implementation adapts hishel 1.0's Entry-based API to work with HARP's
    blob storage system. We store a single entry per cache key, maintaining
    backward compatibility with existing cached data.

    hishel addresses entries by UUID while this store addresses blobs by cache key, so a
    bounded index of recently seen ids bridges the two. See :data:`KEY_INDEX_SIZE` for why a
    small bound is sufficient, and :meth:`_key_for` for what happens when it is not.
    """

    def __init__(
        self,
        storage: IBlobStorage,
        ttl: tp.Optional[tp.Union[int, float]] = None,
        check_ttl_every: tp.Union[int, float] = 60,
        allow_heuristics: bool = False,
    ):
        # Note: hishel 1.0 AsyncBaseStorage.__init__ no longer takes serializer parameter
        super().__init__()

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        self._impl = AsyncStorageAdapter(storage)
        self._storage = storage
        self._ttl = ttl
        self._allow_heuristics = allow_heuristics
        self._keys_by_id: OrderedDict[uuid.UUID, str] = OrderedDict()

    def _remember_key(self, entry_id: uuid.UUID, key: str) -> None:
        """Record how to get back from an entry id to the key its blob is stored under."""
        self._keys_by_id[entry_id] = key
        self._keys_by_id.move_to_end(entry_id)
        while len(self._keys_by_id) > KEY_INDEX_SIZE:
            self._keys_by_id.popitem(last=False)

    def _key_for(self, entry_id: uuid.UUID, operation: str) -> tp.Optional[str]:
        """Resolve an entry id back to its cache key, loudly if it cannot.

        A miss is not a graceful degradation. It means a 304 freshens nothing and the entry
        revalidates on every subsequent request, without end, which is exactly the defect this
        index exists to fix. The symptom is a cache that looks slow rather than broken, so the
        cause has to announce itself here or nobody will connect the two.
        """
        key = self._keys_by_id.get(entry_id)
        if key is None:
            logger.warning(
                f"Cannot {operation} cache entry {entry_id}: no cache key known for it. The entry will not be "
                f"refreshed and will be revalidated on every request. If this recurs, {KEY_INDEX_SIZE} "
                f"(harp_apps.http_cache.storages.KEY_INDEX_SIZE) is too small for this proxy's concurrency."
            )
            return None
        self._keys_by_id.move_to_end(entry_id)
        return key

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

        # The cache key is derived from the request URL alone, so an origin that authenticates
        # its callers by anything other than the `Authorization` header (a cookie, an API key
        # header) is invisible to it. Inventing a freshness lifetime for a response the origin
        # never declared cacheable would then hand one caller's body to the next one, so we
        # keep RFC 9111 §4.2.2 opt-in and simply do not retain such a response.
        if not self._allow_heuristics and not has_explicit_freshness(response):
            logger.debug(f"Cache entry not retained (no explicit freshness, heuristics off): key={key}")
            return entry

        await self._impl.store_entry(key, entry)
        self._remember_key(entry.id, key)
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
                # hishel will address this entry by id if it later needs to freshen or drop it.
                self._remember_key(entry.id, key)
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

        hishel calls this to write a 304's refreshed headers back onto the stored entry. If it
        does nothing, the entry stays exactly as stale as it was and every subsequent request
        revalidates again, without end.

        Args:
            id: The entry UUID
            new_entry: Either a new Entry object or a callable that transforms the existing entry

        Returns:
            The updated Entry, or None if it could not be resolved
        """
        key = self._key_for(id, "update")
        if key is None:
            return None

        entry = await self._impl.retrieve_entry(key)
        if entry is None or entry.id != id:
            # The blob was evicted or replaced between the lookup and here.
            logger.debug(f"Cache entry vanished before update: entry_id={id}, key={key}")
            return None

        updated = new_entry if isinstance(new_entry, Entry) else new_entry(entry)
        await self._impl.store_entry(key, updated)
        logger.debug(f"Cache entry updated: key={key}, entry_id={id}")
        return updated

    async def remove_entry(self, id: uuid.UUID) -> None:
        """Remove an entry by its ID.

        hishel invalidates the stored entries a revalidation did *not* match, which only arises
        where several entries share a cache key. This store holds one entry per key, so hishel
        does not currently reach this method: the lists it builds for invalidation
        (``revalidating_entries[:-1]``, and the non-matching entries after a 304) are always
        empty here. It is implemented rather than left inert because that is a property of the
        storage shape today and not of the contract, and it changes the moment one key can hold
        several variants. See https://github.com/msqd/harp/issues/910.

        Args:
            id: The entry UUID
        """
        key = self._key_for(id, "remove")
        if key is None:
            return

        await self._storage.delete(key)
        self._keys_by_id.pop(id, None)
        logger.debug(f"Cache entry removed: key={key}, entry_id={id}")

    async def close(self) -> None:
        """Close the storage (required by AsyncBaseStorage interface)."""
        logger.debug("Closing AsyncStorage")
        return
