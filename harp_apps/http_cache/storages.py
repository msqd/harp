import asyncio
import time
import typing as tp
import uuid
import weakref
from contextvars import ContextVar
from contextlib import asynccontextmanager
from dataclasses import replace
from email.utils import formatdate
import httpx
from hishel import AsyncBaseStorage, Entry, EntryMeta, Request, Response
from hishel._core._spec import parse_date
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
from .adapters import selecting_headers, to_entry, to_record, variant_of
from .records import BanKind, BanMode, CacheRecords, Reclaimed, endpoint_of
from .settings import ReclamationSettings
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

#: The cache key of the request being handled, set by the transport when it derives it: the transport reports it with the
#: cache outcome, and cannot derive it again once the request has been sent (a body key needs the body).
CACHE_KEY: ContextVar[tp.Optional[str]] = ContextVar("harp_http_cache_key", default=None)

HEADERS_ENCODING = "iso-8859-1"

#: Request metadata key holding the largest response body the cache may store (the proxy's recording cap).
MAX_BODY_SIZE_METADATA = "harp_max_recorded_body_size"

#: Request metadata key holding the :class:`~harp.models.redaction.Redaction` in force for the request.
REDACTION_METADATA = "harp_redaction"

#: Request metadata key holding the markers of the request's transaction.
MARKERS_METADATA = "harp_markers"

#: The storage's :meth:`~AsyncStorage.stamp` read before the request went to the origin, set by the transport. What the
#: origin answers may predate an invalidation that lands meanwhile: an entry made of it carries this stamp, and a ban
#: numbered above it covers the entry.
FETCH_STAMP: ContextVar[tp.Optional[int]] = ContextVar("harp_http_cache_fetch_stamp", default=None)

#: Response metadata key telling which stored variant a response is: ``{"variant": ..., "stamp": ...}``. Set on the
#: entries the storage reads, and on a response it is about to store; the transport reports it with the cache outcome.
ENTRY_METADATA = "harp_cache_entry"

#: Schemes an endpoint is reached by: a cache key starts with the scheme of the request, an endpoint ban covers each.
ENDPOINT_SCHEMES = ("http", "https")

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


def has_validator(response: Response) -> bool:
    """Whether the response carries what a conditional request needs to be answered ``304 Not Modified``."""
    return "etag" in response.headers or "last-modified" in response.headers


def is_retained_for_revalidation(request: Request, response: Response) -> bool:
    """Whether a response without explicit freshness is kept anyway, to be revalidated each time it is wanted.

    A conditional request checks that the validator still matches, not that the stored body belongs to the caller.
    So nothing is kept for a request that carried a credential (ADR-0009's set, rules included): the cache key does
    not see it, and another caller's conditional request would be answered ``304`` with this caller's body. A
    credential under a header no rule declares is invisible here. ``no-cache`` is out too: hishel never reuses such
    an entry, not even by revalidating it. A response setting a cookie is out through :func:`is_withheld`.
    """
    credentials = _redaction_of(request).headers
    return (
        has_validator(response)
        and not parse_cache_control(response.headers.get("cache-control")).no_cache
        and not any(name in credentials for name in request.headers)
    )


#: A date hishel finds so far back that no heuristic freshness lifetime (one week at most) can outlast it.
NEVER_FRESH_DATE = "Thu, 01 Jan 1970 00:00:00 GMT"

#: Carries the stored ``Date`` of an entry shown to hishel as never fresh, until the entry is stored again or served.
ORIGINAL_DATE = "x-harp-original-date"


#: What hishel is shown instead of the freshness an entry stated: no lifetime, and no staleness to be allowed.
#: ``must-revalidate`` is what stops ``allow_stale`` from serving it as it is.
#: The last directive is HARP's own, so that what an origin states, ``max-age=0, must-revalidate`` included, is never
#: mistaken for what HARP showed.
NEVER_FRESH_CACHE_CONTROL = "max-age=0, must-revalidate, x-harp-shown"

#: Carry the stored ``Cache-Control`` and ``Expires`` of an entry shown as never fresh.
STORED_CACHE_CONTROL = "x-harp-stored-cache-control"
STORED_EXPIRES = "x-harp-stored-expires"


def show_as_never_fresh(response: Response, *, revalidate: bool = False) -> None:
    """Make hishel see an entry as stale, so it asks the origin before serving it, whatever the entry says.

    hishel knows no "stored but never fresh" entry, and ages one from its ``Date`` alone. Hence this one is shown
    as dated long ago, and its real ``Date`` kept aside: see :func:`restore_date`. Such an entry may still be served
    stale where the operator allows it (``allow_stale``).

    With ``revalidate``, the entry must be revalidated whatever the policy: hishel would take an ``Expires`` or a
    ``max-age`` for what they say, and serve a stale entry if told to allow it. It is shown with a freshness lifetime
    of 0 and ``must-revalidate``, and its real ``Cache-Control`` and ``Expires`` are kept aside. Validators are left.
    """
    if "date" in response.headers:
        response.headers[ORIGINAL_DATE] = response.headers["date"]
        del response.headers["date"]
    response.headers["date"] = NEVER_FRESH_DATE
    if revalidate:
        _show_as_always_revalidated(response)


def _show_as_always_revalidated(response: Response) -> None:
    headers = response.headers
    # always set, empty when there was none: it is what tells that the entry was shown. Assigning appends, hence the
    # deletes: nothing planted under these names survives.
    _delete(headers, STORED_CACHE_CONTROL, STORED_EXPIRES)
    headers[STORED_CACHE_CONTROL] = ", ".join(headers.get_list("cache-control") or [])
    _delete(headers, "cache-control")
    headers["cache-control"] = NEVER_FRESH_CACHE_CONTROL
    if "expires" in headers:
        headers[STORED_EXPIRES] = headers["expires"]
        del headers["expires"]


def _delete(headers, *names: str) -> None:
    for name in names:
        if name in headers:
            del headers[name]


def drop_harp_headers(headers) -> None:
    """Remove every ``x-harp-*`` header: they are HARP's, and an origin does not get to write them."""
    _delete(headers, *{name for name in headers if name.lower().startswith("x-harp-")})


def restore_date(headers) -> None:
    """Undo :func:`show_as_never_fresh`: a ``304`` that brought its own ``Date``, ``Cache-Control`` or ``Expires``
    keeps it, else the stored one is back."""
    if STORED_CACHE_CONTROL in headers:
        original = headers[STORED_CACHE_CONTROL]
        del headers[STORED_CACHE_CONTROL]
        if headers.get("cache-control") == NEVER_FRESH_CACHE_CONTROL:  # a 304 stating its own is not this one
            del headers["cache-control"]
            if original:
                headers["cache-control"] = original
    if STORED_EXPIRES in headers:
        original = headers[STORED_EXPIRES]
        del headers[STORED_EXPIRES]
        if "expires" not in headers:
            headers["expires"] = original
    if ORIGINAL_DATE not in headers:
        return
    original = headers[ORIGINAL_DATE]
    del headers[ORIGINAL_DATE]
    if headers.get("date") == NEVER_FRESH_DATE:
        del headers["date"]
        headers["date"] = original
        if "age" in headers:  # served stale: its age was counted from the date it was shown with
            del headers["age"]
            headers["age"] = str(max(0, int(time.time() - (parse_date(original) or time.time()))))


class InvalidationError(Exception):
    """An invalidation could not be recorded: the cache still serves what it should not."""


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
        reclamation: tp.Optional[ReclamationSettings] = None,
    ):
        # Note: hishel 1.0 AsyncBaseStorage.__init__ no longer takes serializer parameter
        super().__init__()

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        self._records = records
        self._ttl = ttl
        self._allow_heuristics = allow_heuristics
        self._sweep_task: tp.Optional[asyncio.Task] = None
        self._reclamation = reclamation or ReclamationSettings()
        self._reclaimed_elsewhere = False
        self._refusing: set[str] = set()
        self._refused: dict[str, int] = {}
        self._key_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    @asynccontextmanager
    async def _locked(self, key: str) -> tp.AsyncIterator[None]:
        """Serialize the writers of one cache key in this process: they read a variant, change it and write it back."""
        lock = self._key_locks.get(key) or self._key_locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield

    async def stamp(self) -> int:
        """The invalidation counter, shared by every instance: read before going to the origin, it tells later whether
        what the origin answered was invalidated meanwhile.

        When the counter cannot be read this is ``0``, which every ban is above: whatever is stored from that fetch is
        invalidated by the first ban that covers it.
        """
        try:
            return await self._records.counter()
        except Exception:
            logger.warning("Failed to read the cache invalidation counter", exc_info=True)
            return 0

    async def invalidate(self, key: str, *, mode: BanMode) -> None:
        """Invalidate every variant of a cache key (RFC 9111 §4.4), and the responses of fetches that set out before.

        A soft ban keeps the variants, which are revalidated before they are served. A hard ban makes them unusable,
        and they are deleted.

        Raises:
            InvalidationError: when the ban could not be recorded, and whoever asked must not be told otherwise. A hard
                invalidation still deletes the variants it can, so that the cache serves less of what it should not. A
                hard ban whose entries could not be deleted is recorded, hence done: they are not served, and the
                failure is logged.
        """
        async with self._locked(key):
            try:
                await self._ban(BanKind.EXACT, key, mode, f"key {key}")
            finally:
                if mode is BanMode.HARD:
                    try:
                        await self._records.delete_key(key)
                    except Exception:
                        logger.warning(f"Failed to remove cache entry: key={key}", exc_info=True)

    async def invalidate_endpoint(self, endpoint: str, *, mode: BanMode) -> None:
        """Invalidate everything an endpoint holds. Entries stay in the store until they expire, but are not served.

        Raises:
            InvalidationError: when a ban could not be recorded.
        """
        for scheme in ENDPOINT_SCHEMES:
            try:
                # spelled as the cache keys are: httpx lowercases the host, and so must this
                prefix = str(httpx.URL(f"{scheme}://{endpoint}/"))
            except httpx.InvalidURL as exc:
                raise InvalidationError(f"Cache invalidation of endpoint {endpoint!r}: not a valid host") from exc
            await self._ban(BanKind.PREFIX, prefix, mode, f"endpoint {endpoint}")

    async def invalidate_prefix(self, endpoint: str, path: str, *, mode: BanMode) -> None:
        """Invalidate a path of an endpoint, and everything under it, whatever the query.

        ``/api/users`` covers ``/api/users``, ``/api/users?page=2`` and ``/api/users/42``, not ``/api/usersx``. Entries
        stay in the store until reclamation deletes them (see :meth:`reclaim`), but are not served.

        Raises:
            InvalidationError: when the path is not one, or a ban could not be recorded.
        """
        path = path or "/"
        if not path.startswith("/") or any(char in "?#" or not char.isprintable() or char == " " for char in path):
            raise InvalidationError(f"Cache invalidation of path {path!r}: not a path (it starts with /, has no query)")
        for scheme in ENDPOINT_SCHEMES:
            try:
                url = httpx.URL(f"{scheme}://{endpoint}{path}")
            except httpx.InvalidURL as exc:
                raise InvalidationError(f"Cache invalidation of {endpoint!r}{path!r}: not a valid url") from exc
            prefix = f"{url.scheme}://{url.netloc.decode()}{url.raw_path.decode('ascii')}".rstrip("/")
            if prefix == f"{url.scheme}://{url.netloc.decode()}":
                await self._ban(BanKind.PREFIX, prefix + "/", mode, f"endpoint {endpoint}")
            else:
                await self._ban(BanKind.PREFIX, prefix, mode, f"path {path} of endpoint {endpoint}")

    async def invalidate_all(self, *, mode: BanMode) -> None:
        """Invalidate everything the cache holds. Entries stay in the store until they expire, but are not served.

        Raises:
            InvalidationError: when the ban could not be recorded.
        """
        await self._ban(BanKind.PREFIX, "", mode, "everything")

    async def _ban(self, kind: BanKind, prefix: str, mode: BanMode, what: str) -> None:
        try:
            await self._records.ban(kind, prefix, mode)
        except Exception as exc:
            raise InvalidationError(f"Cache invalidation of {what} could not be recorded") from exc

    def delegate_reclamation(self) -> tp.Callable[[], tp.Awaitable[Reclaimed]]:
        """Hand :meth:`reclaim` to a worker that will run it (the janitor), once, when the application is bound.

        The sweep of this storage then leaves reclaiming to it. Without a worker the sweep does it, which is all there
        is to run it when the storage application, hence the janitor, is not loaded.
        """
        self._reclaimed_elsewhere = True
        return self.reclaim

    async def reclaim(self, *, grace: tp.Optional[float] = None) -> Reclaimed:
        """Delete what the old bans cover and retire them, then the bodies and resources nothing refers to.

        Meant for a worker that runs it from time to time (the janitor): bounded by the ``rounds`` and ``entries`` of the
        reclamation settings, resumed where it stopped by the next run. A hard ban is retired when what it
        covers is deleted. A soft ban is not: its entries are revalidated, not deleted, so it is retired only when none is
        left that it makes stale (revalidated, replaced, expired or deleted), and until then it keeps the entries stale
        and costs a ban in the log. Bans younger than ``grace`` seconds (by default the setting) are left alone.
        """
        settings = self._reclamation
        total = Reclaimed()
        for _ in range(settings.rounds):
            run = await self._records.reclaim(
                older_than=time.time() - (settings.grace if grace is None else grace),
                bans=settings.bans,
                entries=settings.entries,
            )
            total = Reclaimed(total.retired + run.retired, total.deleted + run.deleted, run.pending)
            if not run.pending:
                break
            await asyncio.sleep(0)
        orphans = await self._records.reclaim_orphans(limit=settings.entries)
        if total.retired or total.deleted or orphans:
            logger.debug(
                f"Cache reclamation retired {total.retired} bans, deleted {total.deleted} entries and {orphans} orphans"
            )
        return total

    def _is_expired(self, stored_at: float) -> bool:
        return self._ttl is not None and time.time() - stored_at > self._ttl

    def _sweep_if_due(self) -> None:
        """Start a background sweep if one is due, at most one at a time and once per `check_ttl_every`.

        Never awaited by the request: the sweep is work no proxied request should wait for.
        """
        if self._ttl is None and not self._refused and self._reclaimed_elsewhere:
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
        """Flush the refused counts, delete the entries not written for more than `ttl` by batch, and reclaim the bans
        unless the janitor does."""
        try:
            await self.flush_counters()
            if self._ttl is not None:
                removed = 0
                while True:
                    deleted = await self._records.delete_stored_before(
                        time.time() - self._ttl, limit=SWEEP_DELETE_BATCH
                    )
                    removed += deleted
                    if deleted < SWEEP_DELETE_BATCH:
                        break
                    await asyncio.sleep(0)
                if removed:
                    logger.debug(f"Cache ttl sweep removed {removed} entries")
            if not self._reclaimed_elsewhere:
                await self.reclaim()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Cache ttl sweep failed")

    async def _store_variant(self, entry: Entry, redaction: Redaction, stamp: int) -> bool:
        """Add an entry to the variants of its key: it replaces the variant it supersedes, and pushes out the oldest.

        Nothing is added if the key was invalidated since ``stamp``: the response may show the resource as it was.
        """
        record, body = await to_record(entry, redaction, stamp=stamp)
        async with self._locked(record.key):
            if not await self._records.put(record, body, keep=MAX_VARIANTS_PER_KEY):
                logger.debug(f"Cache entry not retained (key invalidated while in flight): key={record.key}")
                return False
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
            f"Creating cache entry: key={key}, "
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
        # keep RFC 9111 §4.2.2 opt-in. Such a response is retained only when it carries a validator,
        # as an entry that is never fresh: the origin confirms it each time (see `get_entries`).
        if (
            not self._allow_heuristics
            and not has_explicit_freshness(response)
            and not is_retained_for_revalidation(request, response)
        ):
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

        # Read now, while the context is the request's: the body ends in the client's.
        stamp = FETCH_STAMP.get() or 0
        response.metadata[ENTRY_METADATA] = {
            "variant": variant_of(selecting_headers(request, response)),
            "stamp": stamp,
        }

        async def store(body: bytes) -> None:
            try:
                stored = await self._store_variant(
                    replace(entry, response=replace(entry.response, stream=make_async_iterator([body]))),
                    _redaction_of(request),
                    stamp,
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
        # counted here, written later: the endpoint's counter row is not worth a wait on the request path
        self._refused[endpoint] = self._refused.get(endpoint, 0) + 1
        self._sweep_if_due()

    async def flush_counters(self) -> None:
        """Write the refusals counted since the last time."""
        pending, self._refused = self._refused, {}
        for endpoint, count in pending.items():
            try:
                await self._records.count_refused(endpoint, count)
            except Exception:
                self._refused[endpoint] = self._refused.get(endpoint, 0) + count
                logger.warning(f"Failed to count refused cache entries: endpoint={endpoint}", exc_info=True)

    def _is_never_fresh(self, response: Response) -> bool:
        """Whether the origin gave no expiry and, heuristics being off, none may be invented: only it can say."""
        return not self._allow_heuristics and not has_explicit_freshness(response)

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
            for variant, entry in zip(live, entries):
                entry.response.metadata[ENTRY_METADATA] = {
                    "variant": variant.record.variant,
                    "stamp": variant.record.stamp,
                }
                if variant.record.stale or self._is_never_fresh(entry.response):
                    show_as_never_fresh(entry.response, revalidate=variant.record.stale)
                logger.debug(f"Cache hit: key={key}, method={entry.request.method}, entry_id={entry.id}")
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
                if stored.record.stale or self._is_never_fresh(entry.response):
                    show_as_never_fresh(entry.response, revalidate=stored.record.stale)
                updated = new_entry if isinstance(new_entry, Entry) else new_entry(entry)
                # the stored url holds no secret and is not the update's to change
                updated = replace(updated, request=replace(updated.request, url=entry.request.url))
                restore_date(updated.response.headers)
                if is_withheld(updated.request, updated.response):
                    # A revalidation brought in a header that must not be stored: the entry goes, not the header.
                    await self._records.delete_entry(id)
                    return None
                # What the origin just confirmed is current as of the fetch that asked it, which may be later than the
                # stamp of the entry: a soft ban between the two is lifted. Without a fetch, the stamp stays.
                stamp = max(located.stamp, FETCH_STAMP.get() or 0)
                record, body = await to_record(updated, stamp=stamp)
                if not await self._records.put(record, body, keep=MAX_VARIANTS_PER_KEY, replaces=id):
                    logger.debug(f"Cache entry not updated (invalidated while in flight): key={key}, entry_id={id}")
                    return None
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
        await self.flush_counters()
        await self._records.close()
