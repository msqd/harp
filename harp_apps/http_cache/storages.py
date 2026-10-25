import asyncio
import time
import typing as tp
import uuid
import weakref
from contextvars import ContextVar
from contextlib import asynccontextmanager
from collections import OrderedDict
from dataclasses import replace
from email.utils import formatdate
from hishel import AsyncBaseStorage, Entry, EntryMeta, Request, Response
from hishel._utils import make_async_iterator

from harp import get_logger
from harp.models.redaction import REDACTED, Redaction
from harp.http.utils import parse_cache_control
from harp_apps.storage.constants import (
    DEFAULT_MAX_RECORDED_BODY_SIZE,
    SKIP_REQUEST_STORAGE,
    SKIP_RESPONSE_STORAGE,
)
from .coalescing import STORED_METADATA
from .adapters import to_entry, to_record
from .records import CacheRecords, endpoint_of
from .streams import StoredOnceRead

# How many expired entries the sweep deletes at once.
SWEEP_DELETE_BATCH = 200

DEFAULT_TTL = 86400

#: How many variants of a ``Vary`` resource one cache key holds. Storing one more evicts the oldest stored.
MAX_VARIANTS_PER_KEY = 8

#: The longest path, in bytes, of a cache key that is stored. Keys are indexed, and PostgreSQL refuses to index values
#: past a third of a page (about 2.7 kB): a longer one would be refused on that backend only.
MAX_KEY_SIZE = 2048

logger = get_logger(__name__)

#: The url of the request being looked up, set by the transport when it derives the cache key. The stored entries hold
#: their url with the values of redacted query parameters replaced (ADR-0009), while hishel matches an entry by its
#: whole url: :meth:`AsyncStorage.get_entries` gives them the url of the request they match.
REQUEST_URL: ContextVar[tp.Optional[str]] = ContextVar("harp_http_cache_request_url", default=None)

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
    compared or replayed (ADR-0009). Hence two cases where nothing is stored at all: the response varies on a
    redacted header, or it carries a redacted header itself. What an operator keeps out of storage with a
    ``skip-*-storage`` marker stays out of the cache too. A redacted query parameter does not withhold the response:
    the key holds a hash of the query, and the query kept for display has the value replaced.
    """
    if _SKIP_MARKERS & set(request.metadata.get(MARKERS_METADATA) or ()):
        return True

    redaction = _redaction_of(request)
    if any(name.strip() in redaction.headers for name in ",".join(response.headers.get_list("vary") or []).split(",")):
        return True
    return any(name in redaction.headers for name in response.headers)


def _same_url_but_redacted(stored: str, current: str) -> bool:
    """Whether ``stored`` is ``current`` with the value of some query parameters replaced by the placeholder."""
    stored_path, _, stored_query = stored.partition("?")
    path, _, query = current.partition("?")
    stored_parameters, parameters = stored_query.split("&"), query.split("&")
    return (
        stored_path == path
        and len(stored_parameters) == len(parameters)
        and all(
            kept == given or kept == f"{given.partition('=')[0]}={REDACTED}"
            for kept, given in zip(stored_parameters, parameters)
        )
    )


def has_explicit_freshness(response: Response) -> bool:
    """Whether the origin stated how long its response stays fresh.

    Mirrors the first three rules of RFC 9111 §4.2.1 (``s-maxage``, ``max-age``, ``Expires``)
    and deliberately stops before the fourth, which is the ``Last-Modified`` heuristic.
    """
    cache_control = parse_cache_control(response.headers.get("cache-control"))
    return cache_control.s_maxage is not None or cache_control.max_age is not None or "expires" in response.headers


#: How many invalidated keys the storage remembers. Past it the oldest are forgotten, and every request that set out
#: before the newest forgotten one is treated as invalidated: some responses go unstored, none is stored stale.
INVALIDATION_LOG_SIZE = 8192


class AsyncStorage(AsyncBaseStorage):
    """HARP's AsyncBaseStorage implementation, on indexed cache records (ADR-0014).

    This implementation adapts hishel 1.0's Entry-based API to the records of a :class:`CacheRecords` backend: one per
    cache key, and one per variant of its resource, at most :data:`MAX_VARIANTS_PER_KEY`. hishel addresses entries by
    UUID, which the records find directly.
    """

    def __init__(
        self,
        records: CacheRecords,
        ttl: tp.Optional[tp.Union[int, float]] = DEFAULT_TTL,
        check_ttl_every: tp.Union[int, float] = 60,
        allow_heuristics: bool = False,
    ):
        # Note: hishel 1.0 AsyncBaseStorage.__init__ no longer takes serializer parameter
        super().__init__()

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        self._records = records
        self._ttl = ttl
        self._allow_heuristics = allow_heuristics
        self._sweep_task: tp.Optional[asyncio.Task] = None
        self._refusing: set[str] = set()
        self._stamp = 0
        self._invalidated_at: OrderedDict[str, int] = OrderedDict()
        self._forgotten_up_to = 0
        self._key_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    @asynccontextmanager
    async def _locked(self, key: str) -> tp.AsyncIterator[None]:
        """Serialize the writers of one cache key in this process: they read a variant, change it and write it back."""
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
                await self._records.delete_key(key)
            except Exception:
                logger.warning(f"Failed to remove cache entry: key={key}", exc_info=True)

    def _is_expired(self, stored_at: float) -> bool:
        return self._ttl is not None and time.time() - stored_at > self._ttl

    def _sweep_if_due(self) -> None:
        """Start a background sweep if one is due, at most one at a time and once per `check_ttl_every`.

        Never awaited by the request: the sweep is work no proxied request should wait for.
        """
        if self._ttl is None:
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

    async def _sweep(self) -> None:
        """Delete the entries not written for more than `ttl`, by batch, yielding to the event loop along the way."""
        try:
            removed = 0
            while True:
                deleted = await self._records.delete_stored_before(time.time() - self._ttl, limit=SWEEP_DELETE_BATCH)
                removed += deleted
                if deleted < SWEEP_DELETE_BATCH:
                    break
                await asyncio.sleep(0)
            if removed:
                logger.debug(f"Cache ttl sweep removed {removed} entries")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Cache ttl sweep failed")

    async def _store_variant(self, entry: Entry, redaction: Redaction, stamp: tp.Optional[int]) -> bool:
        """Add an entry to the variants of its key: it replaces the variant it supersedes, and pushes out the oldest.

        Nothing is added if the key was invalidated since ``stamp``: the response may show the resource as it was.
        """
        record, body = await to_record(entry, redaction)
        async with self._locked(record.key):
            if stamp is not None and self._invalidated_since(record.key, stamp):
                logger.debug(f"Cache entry not retained (key invalidated while in flight): key={record.key}")
                return False
            await self._records.put(record, body, keep=MAX_VARIANTS_PER_KEY)
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

        if len(key.partition("?")[0].encode("utf-8")) > MAX_KEY_SIZE:
            await self._refuse(key)
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

    async def _refuse(self, key: str) -> None:
        """A path too long to be indexed: say so once per endpoint, and count it, so that it is seen why it never caches."""
        endpoint = endpoint_of(key)
        if endpoint not in self._refusing:
            self._refusing.add(endpoint)
            logger.warning(
                f"Cache entry not retained, path over {MAX_KEY_SIZE} bytes (further ones are counted, not logged): "
                f"endpoint={endpoint} key={key[:80]}..."
            )
        try:
            await self._records.count_refused(endpoint)
        except Exception:
            logger.warning(f"Failed to count a refused cache entry: endpoint={endpoint}", exc_info=True)

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
            stored = await self._records.get_variants(key)
            live = [variant for variant in stored if not self._is_expired(variant.record.stored_at)]
            if len(live) < len(stored):
                logger.debug(f"Cache entry expired: key={key}")
                await self._prune(key, [variant.record.entry_id for variant in stored if variant not in live])
            entries = [self._with_request_url(to_entry(variant)) for variant in live]
            for entry in entries:
                logger.debug(
                    f"Cache hit: key={key}, url={entry.request.url}, method={entry.request.method}, entry_id={entry.id}"
                )
            if not entries:
                logger.debug(f"Cache miss: key={key}")
            return entries
        except Exception:
            # Unexpected error - log full traceback
            logger.exception(f"Failed to retrieve cache for key={key}")
            return []

    @staticmethod
    def _with_request_url(entry: Entry) -> Entry:
        """The entry, its request url the one being looked up when it is the stored one but for redacted values."""
        current = REQUEST_URL.get()
        if current and current != entry.request.url and _same_url_but_redacted(entry.request.url, current):
            return replace(entry, request=replace(entry.request, url=current))
        return entry

    async def _prune(self, key: str, entry_ids: list[uuid.UUID]) -> None:
        """Drop the variants of a key that have expired."""
        async with self._locked(key):
            for entry_id in entry_ids:
                await self._records.delete_entry(entry_id)

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
        try:
            located = await self._records.get_by_id(id)
            if located is None:
                # The variant was evicted, replaced or expired between the lookup and here.
                logger.debug(f"Cache entry vanished before update: entry_id={id}")
                return None
            key = located.key

            async with self._locked(key):
                stored = next((v for v in await self._records.get_variants(key) if v.record.entry_id == id), None)
                if stored is None:
                    logger.debug(f"Cache entry vanished before update: entry_id={id}, key={key}")
                    return None

                entry = to_entry(stored)
                updated = new_entry if isinstance(new_entry, Entry) else new_entry(entry)
                # the stored url holds no secret and is not the update's to change
                updated = replace(updated, request=replace(updated.request, url=entry.request.url))
                if is_withheld(updated.request, updated.response):
                    # A revalidation brought in a header that must not be stored: the entry goes, not the header.
                    await self._records.delete_entry(id)
                    return None
                record, body = await to_record(updated)
                await self._records.put(record, body, keep=MAX_VARIANTS_PER_KEY, replaces=id)
        except Exception:
            logger.warning(f"Failed to update cache entry: entry_id={id}", exc_info=True)
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
        try:
            removed = await self._records.delete_entry(id)
        except Exception:
            logger.warning(f"Failed to remove cache entry: entry_id={id}", exc_info=True)
            return
        logger.debug(f"Cache entry removed: entry_id={id}" if removed else f"Cache entry already gone: entry_id={id}")

    async def close(self) -> None:
        """Close the storage (required by AsyncBaseStorage interface)."""
        logger.debug("Closing AsyncStorage")
        if self._sweep_task is not None:
            self._sweep_task.cancel()
        await self._records.close()
