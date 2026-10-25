import asyncio
import time
import typing as tp
import uuid
import weakref
from contextlib import asynccontextmanager
from collections import OrderedDict
from dataclasses import replace
import yaml
from email.utils import formatdate
from urllib.parse import parse_qsl, urlsplit
from hishel import AsyncBaseStorage, Entry, EntryMeta, Request, Response
from hishel._utils import make_async_iterator

from harp import get_logger
from harp.models import Blob
from harp.models.redaction import Redaction
from harp.http.utils import parse_cache_control
from harp_apps.storage.constants import (
    DEFAULT_MAX_RECORDED_BODY_SIZE,
    SKIP_REQUEST_STORAGE,
    SKIP_RESPONSE_STORAGE,
)
from harp_apps.storage.types import IBlobStorage
from .coalescing import STORED_METADATA
from .adapters import AsyncStorageAdapter, stored_at_of, variant_id, variants_of
from .streams import StoredOnceRead

# libyaml's loader decodes an entry about ten times faster than the pure Python one.
_YamlLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# How many entries the sweep decodes before handing the event loop back.
SWEEP_YIELD_EVERY = 50

# How many expired entries the sweep deletes at once.
SWEEP_DELETE_BATCH = 200

CACHE_META_CONTENT_TYPE = "cache/meta"
DEFAULT_TTL = 86400

#: How many variants of a ``Vary`` resource one cache key holds. Storing one more evicts the oldest stored.
MAX_VARIANTS_PER_KEY = 8

logger = get_logger(__name__)
HEADERS_ENCODING = "iso-8859-1"

#: Request metadata key holding the largest response body the cache may store (the proxy's recording cap).
MAX_BODY_SIZE_METADATA = "harp_max_recorded_body_size"

#: Request metadata key holding the :class:`~harp.models.redaction.Redaction` in force for the request.
REDACTION_METADATA = "harp_redaction"

#: Request metadata key holding the markers of the request's transaction.
MARKERS_METADATA = "harp_markers"

#: Request metadata key holding the storage's :attr:`~AsyncStorage.stamp` when the request set out. A response is not
#: stored if its key was invalidated after that.
STAMP_METADATA = "harp_invalidation_stamp"

#: Markers that keep a transaction's messages out of storage, the cache included. ``skip-storage`` is not one:
#: the storage worker sets it itself under pressure, and load must not switch the cache off.
_SKIP_MARKERS = frozenset({SKIP_REQUEST_STORAGE, SKIP_RESPONSE_STORAGE})


def _redaction_of(request: Request) -> Redaction:
    return request.metadata.get(REDACTION_METADATA) or Redaction()


def is_withheld(request: Request, response: Response) -> bool:
    """Whether this exchange must stay out of the cache, because storing it would keep a credential.

    The cache reads back what it stores to answer requests, so a redacted value is only safe where it is never
    compared or replayed (ADR-0009). Hence three cases where nothing is stored at all: the response varies on a
    redacted header, its URL carries a redacted query parameter, or it carries a redacted header itself. What an
    operator keeps out of storage with a ``skip-*-storage`` marker stays out of the cache too.
    """
    if _SKIP_MARKERS & set(request.metadata.get(MARKERS_METADATA) or ()):
        return True

    redaction = _redaction_of(request)
    if any(name.strip() in redaction.headers for name in ",".join(response.headers.get_list("vary") or []).split(",")):
        return True
    if any(name in redaction.headers for name in response.headers):
        return True
    return any(name in redaction.query for name, _ in parse_qsl(urlsplit(request.url).query, keep_blank_values=True))


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

#: How many invalidated keys the storage remembers. Past it the oldest are forgotten, and every request that set out
#: before the newest forgotten one is treated as invalidated: some responses go unstored, none is stored stale.
INVALIDATION_LOG_SIZE = 8192


class AsyncStorage(AsyncBaseStorage):
    """HARP's AsyncBaseStorage implementation using blob storage backend.

    This implementation adapts hishel 1.0's Entry-based API to work with HARP's
    blob storage system. A cache key holds the variants of its resource, at most
    :data:`MAX_VARIANTS_PER_KEY`, in one blob; a blob written before variants existed
    reads as a single one.

    hishel addresses entries by UUID while this store addresses blobs by cache key, so a
    bounded index of recently seen ids bridges the two. See :data:`KEY_INDEX_SIZE` for why a
    small bound is sufficient, and :meth:`_key_for` for what happens when it is not.
    """

    def __init__(
        self,
        storage: IBlobStorage,
        ttl: tp.Optional[tp.Union[int, float]] = DEFAULT_TTL,
        check_ttl_every: tp.Union[int, float] = 60,
        allow_heuristics: bool = False,
    ):
        # Note: hishel 1.0 AsyncBaseStorage.__init__ no longer takes serializer parameter
        super().__init__()

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        if ttl is not None and not hasattr(storage, "iter_blobs"):
            logger.warning(
                f"{type(storage).__name__} cannot enumerate cache entries: the http_cache.storage `ttl` setting "
                "will not reclaim storage. Entries expire when read, but unread ones are never deleted."
            )
        self._impl = AsyncStorageAdapter(storage)
        self._storage = storage
        self._ttl = ttl
        self._allow_heuristics = allow_heuristics
        self._keys_by_id: OrderedDict[uuid.UUID, str] = OrderedDict()
        self._sweep_task: tp.Optional[asyncio.Task] = None
        self._stamp = 0
        self._invalidated_at: OrderedDict[str, int] = OrderedDict()
        self._forgotten_up_to = 0
        self._key_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    @asynccontextmanager
    async def _locked(self, key: str) -> tp.AsyncIterator[None]:
        """Serialize the writers of one cache key: they read the variants, change them and write them all back."""
        lock = self._key_locks.get(key) or self._key_locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield

    @property
    def stamp(self) -> int:
        """Counts the invalidations so far: read when a request sets out, it tells later whether its key was invalidated since."""
        return self._stamp

    def _invalidated_since(self, key: str, stamp: int) -> bool:
        return self._invalidated_at.get(key, self._forgotten_up_to) > stamp

    async def invalidate(self, key: str) -> None:
        """Drop every variant of a key, and refuse the responses of requests that set out before (RFC 9111 §4.4)."""
        async with self._locked(key):
            self._stamp += 1
            self._invalidated_at[key] = self._stamp
            self._invalidated_at.move_to_end(key)
            while len(self._invalidated_at) > INVALIDATION_LOG_SIZE:
                self._forgotten_up_to = self._invalidated_at.popitem(last=False)[1]
            try:
                await self._impl.write_variants(key, [])
            except Exception:
                logger.warning(f"Failed to remove cache entry: key={key}", exc_info=True)

    async def _prune(self, key: str) -> None:
        """Drop the expired variants of a key, and the key itself when none is left."""
        async with self._locked(key):
            variants = await self._impl.load_variants(key)
            live = [variant for variant in variants if not self._is_expired(stored_at_of(variant))]
            if len(live) < len(variants):
                await self._impl.write_variants(key, live)

    def _is_expired(self, stored_at: float) -> bool:
        return self._ttl is not None and time.time() - stored_at > self._ttl

    def _sweep_if_due(self) -> None:
        """Start a background sweep if one is due, at most one at a time and once per `check_ttl_every`.

        Never awaited by the request: decoding every entry is work no proxied request should wait for.
        """
        if self._ttl is None or not hasattr(self._storage, "iter_blobs"):
            return
        if self._sweep_task is not None and not self._sweep_task.done():
            return
        if time.monotonic() - self._last_cleaned < self._check_ttl_every:
            return
        self._last_cleaned = time.monotonic()
        self._sweep_task = asyncio.create_task(self._sweep())

    async def wait_for_sweep(self) -> None:
        """Wait for the running sweep, if any, to end."""
        if self._sweep_task is not None:
            await asyncio.gather(self._sweep_task, return_exceptions=True)

    async def _delete_expired(self, expired: list[Blob]) -> int:
        """Delete expired entries, sparing any that were stored again since they were read."""
        if not expired:
            return 0
        if hasattr(self._storage, "delete_blobs"):
            await self._storage.delete_blobs(expired)
        else:
            for blob in expired:
                await self._storage.delete(blob.id)
        await asyncio.sleep(0)
        return len(expired)

    async def _sweep(self) -> None:
        """Delete the entries not written for more than `ttl`, yielding to the event loop along the way."""
        try:
            expired: list[Blob] = []
            removed = 0
            seen = 0
            async for blob in self._storage.iter_blobs(CACHE_META_CONTENT_TYPE):
                try:
                    variants = variants_of(yaml.load(blob.data, Loader=_YamlLoader))
                    live = [variant for variant in variants if not self._is_expired(stored_at_of(variant))]
                    if not live:
                        expired.append(blob)
                    elif len(live) < len(variants):
                        await self._prune(blob.id)
                except Exception:
                    logger.exception(f"Unreadable cache entry, left alone: key={blob.id}")
                if len(expired) >= SWEEP_DELETE_BATCH:
                    removed += await self._delete_expired(expired)
                    expired = []
                seen += 1
                if seen % SWEEP_YIELD_EVERY == 0:
                    await asyncio.sleep(0)
            removed += await self._delete_expired(expired)
            if removed:
                logger.debug(f"Cache ttl sweep removed {removed} entries")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Cache ttl sweep failed")

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

    async def _store_variant(self, key: str, entry: Entry, redaction: Redaction, stamp: tp.Optional[int]) -> bool:
        """Add an entry to the variants of its key: it replaces the variant it supersedes, and pushes out the oldest.

        Nothing is added if the key was invalidated since ``stamp``: the response may show the resource as it was.
        """
        variant = await self._impl.serialize_variant(entry, redaction)
        async with self._locked(key):
            if stamp is not None and self._invalidated_since(key, stamp):
                logger.debug(f"Cache entry not retained (key invalidated while in flight): key={key}")
                return False
            kept = [
                stored
                for stored in await self._impl.load_variants(key)
                if not self._is_expired(stored_at_of(stored)) and stored.get("selecting") != variant["selecting"]
            ]
            await self._impl.write_variants(key, [*kept, variant][-MAX_VARIANTS_PER_KEY:])
        return True

    async def create_entry(
        self,
        request: Request,
        response: Response,
        key: str,
        id_: tp.Optional[uuid.UUID] = None,
    ) -> Entry:
        """Create a new cache entry, stored once its response body has been read to the end.

        The returned entry's response streams the body as it arrives, so nothing waits for the whole of it. A body
        over the proxy's recording cap (request metadata, see :data:`MAX_BODY_SIZE_METADATA`) is not stored.

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
            response.metadata["hishel_stored"] = False
            return entry

        if is_withheld(request, response):
            logger.debug(f"Cache entry not retained (withheld, see ADR-0009): key={key}")
            response.metadata["hishel_stored"] = False
            return entry

        # RFC 9110 §6.6.1: a cache without a `Date` to age the response against must record its
        # time of receipt, or hishel computes an age of 0 and the response never goes stale.
        if "date" not in response.headers:
            response.headers["date"] = formatdate(entry.meta.created_at, usegmt=True)

        limit = request.metadata.get(MAX_BODY_SIZE_METADATA)
        if limit is None:
            limit = DEFAULT_MAX_RECORDED_BODY_SIZE

        async def store(body: bytes) -> None:
            try:
                stored = await self._store_variant(
                    key,
                    replace(entry, response=replace(entry.response, stream=make_async_iterator([body]))),
                    _redaction_of(request),
                    request.metadata.get(STAMP_METADATA),
                )
            except Exception:
                # The upstream served this response correctly: a cache that cannot keep it must not break it.
                logger.warning(f"Failed to store cache entry, response not cached: key={key}", exc_info=True)
                return
            if not stored:
                return
            self._remember_key(entry.id, key)
            response.metadata[STORED_METADATA] = True
            logger.debug(f"Cache entry stored: key={key}")
            self._sweep_if_due()

        # The entry is stored once its body has been read to the end, as it reaches the client.
        return replace(
            entry,
            response=replace(
                response,
                stream=StoredOnceRead(
                    response.stream,
                    limit=limit,
                    on_end=store,
                    content_encoding=response.headers.get("content-encoding"),
                ),
            ),
        )

    async def get_entries(self, key: str) -> tp.List[Entry]:
        """Retrieve all entries for a given cache key: its unexpired variants, oldest stored first.

        Args:
            key: The cache key

        Returns:
            List of Entry objects (empty if not found)
        """
        logger.debug(f"Retrieving cache entries: key={key}")
        try:
            self._sweep_if_due()
            variants = await self._impl.load_variants(key)
            live = [variant for variant in variants if not self._is_expired(stored_at_of(variant))]
            if len(live) < len(variants):
                logger.debug(f"Cache entry expired: key={key}")
                await self._prune(key)
            entries = []
            for variant in live:
                try:
                    entry = await self._impl.unserialize_variant(key, variant)
                except ValueError as e:
                    # Incomplete cache entry - log warning and treat as cache miss
                    logger.warning(f"Cache entry incomplete for key={key}: {e}")
                    continue
                # hishel will address this entry by id if it later needs to freshen or drop it.
                self._remember_key(entry.id, key)
                logger.debug(
                    f"Cache hit: key={key}, url={entry.request.url}, method={entry.request.method}, entry_id={entry.id}"
                )
                entries.append(entry)
            if not entries:
                logger.debug(f"Cache miss: key={key}")
            return entries
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

        try:
            async with self._locked(key):
                variants = await self._impl.load_variants(key)
                position = next((n for n, variant in enumerate(variants) if variant_id(key, variant) == id), None)
                if position is None:
                    # The variant was evicted or replaced between the lookup and here.
                    logger.debug(f"Cache entry vanished before update: entry_id={id}, key={key}")
                    return None

                entry = await self._impl.unserialize_variant(key, variants[position])
                updated = new_entry if isinstance(new_entry, Entry) else new_entry(entry)
                if is_withheld(updated.request, updated.response):
                    # A revalidation brought in a header that must not be stored: the entry goes, not the header.
                    await self._impl.write_variants(key, variants[:position] + variants[position + 1 :])
                    self._keys_by_id.pop(id, None)
                    return None
                variants[position] = await self._impl.serialize_variant(updated)
                await self._impl.write_variants(key, variants)
        except Exception:
            logger.warning(f"Failed to update cache entry: key={key}, entry_id={id}", exc_info=True)
            return None
        logger.debug(f"Cache entry updated: key={key}, entry_id={id}")
        return updated

    async def remove_entry(self, id: uuid.UUID) -> None:
        """Remove an entry by its ID.

        hishel invalidates the stored entries a revalidation did *not* match, which arises where
        several entries share a cache key: the variants of a ``Vary`` resource. Only the variant
        with this id goes; the others stay.

        Args:
            id: The entry UUID
        """
        key = self._key_for(id, "remove")
        if key is None:
            return

        try:
            async with self._locked(key):
                variants = await self._impl.load_variants(key)
                await self._impl.write_variants(key, [v for v in variants if variant_id(key, v) != id])
        except Exception:
            logger.warning(f"Failed to remove cache entry: key={key}, entry_id={id}", exc_info=True)
            return
        self._keys_by_id.pop(id, None)
        logger.debug(f"Cache entry removed: key={key}, entry_id={id}")

    async def close(self) -> None:
        """Close the storage (required by AsyncBaseStorage interface)."""
        logger.debug("Closing AsyncStorage")
        if self._sweep_task is not None:
            self._sweep_task.cancel()
