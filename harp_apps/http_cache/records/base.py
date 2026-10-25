import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple, Optional
from urllib.parse import urlsplit


def endpoint_of(key: str) -> str:
    """The endpoint a cache key belongs to: the key is the request url, its host replaced by the endpoint name."""
    return urlsplit(key).netloc


def digest_of(data: bytes) -> str:
    """The content digest bodies are stored under: sha256, in hexadecimal."""
    return hashlib.sha256(data).hexdigest()


def ban_prefixes(key: str) -> list[str]:
    """The prefixes a prefix ban can cover a key by: everything, its endpoint, and each directory of its path.

    A prefix ends with a ``/``, so ``http://api/items/`` covers ``http://api/items/1`` and not ``http://api/itemsx``.
    Checking a key against the bans costs as many lookups as it has prefixes, never as many as there are bans.
    """
    path = key.partition("?")[0]
    start = path.find("/", path.find("://") + 3)
    if start == -1:
        return ["", path + "/"]
    prefixes = [""]
    while start != -1:
        prefixes.append(path[: start + 1])
        start = path.find("/", start + 1)
    return prefixes


class BanKind(StrEnum):
    """What a ban covers: one cache key, or every key that starts with its prefix (an endpoint, a directory, all)."""

    EXACT = "exact"
    PREFIX = "prefix"


class BanMode(StrEnum):
    """What a ban does to the entries it covers (RFC 9111 §4.4)."""

    #: The entries are stale: kept, and revalidated with their validators before they are served.
    SOFT = "soft"

    #: The entries are unusable.
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class Ban:
    """One invalidation, appended to the log. An entry stamped below ``seq`` that the ban covers is invalidated."""

    #: The number the invalidation counter gave it: bans are numbered in the order they commit.
    seq: int
    kind: BanKind

    #: The cache key for an exact ban. For a prefix ban, the start of the keys it covers: ``scheme://endpoint/`` for an
    #: endpoint, the empty string for everything.
    prefix: str
    mode: BanMode

    #: POSIX seconds.
    created_at: float


@dataclass(frozen=True, slots=True)
class VariantRecord:
    """One stored response of a resource: what a cache key holds for one combination of ``Vary`` request headers.

    The resource record itself is the cache key (the URL, its host replaced by the endpoint name), which orders the
    records by endpoint, then path. The body is stored apart, by content digest.
    """

    #: Cache key of the resource this is a variant of.
    key: str

    #: Digest of the request header values the response varies on, empty when it does not vary.
    variant: str

    #: Stable across 304 freshening, new when the response is replaced. What hishel addresses an entry by.
    entry_id: uuid.UUID

    #: The endpoint the key belongs to.
    endpoint: str

    #: The invalidation counter read before the origin fetch. A ban whose number is higher covers the variant: it is
    #: unusable (hard) or stale (soft), and a variant is not stored if a ban already covers it. ``0`` is covered by every
    #: ban.
    stamp: int

    status: int

    #: Header names the response varies on, as it nominated them.
    vary: Optional[str]

    #: Digest of the body, see :func:`digest_of`.
    body_digest: str
    body_size: int

    #: When the response was created, then last written (stored or freshened by a 304), POSIX seconds.
    created_at: float
    stored_at: float

    #: The request and response heads, serialized by :mod:`harp_apps.http_cache.adapters`.
    head: bytes

    #: The query string of the request, for display only: the values of redacted parameters (ADR-0009) are replaced.
    #: The key holds a hash of the whole query, never its values.
    query: Optional[str] = None

    #: Set when reading: a soft ban covers the variant, which must be revalidated before it is served. Not stored.
    stale: bool = False


class StoredVariant(NamedTuple):
    """A variant record, with its body."""

    record: VariantRecord
    body: bytes


@dataclass(frozen=True, slots=True)
class EndpointStats:
    """What an endpoint holds: kept on write, never counted."""

    endpoint: str
    entries: int
    bytes: int

    #: Responses that were not stored because their key was too long.
    refused: int = 0


class CacheRecords(ABC):
    """Where the cache keeps its records (ADR-0014): one per resource, one per variant, bodies by content digest.

    A body is shared by the records carrying it, and deleted with the last one. Counters per endpoint are kept as
    records are written and deleted. Every method is safe to run concurrently with the others.
    """

    @abstractmethod
    async def get_variants(self, key: str) -> list[StoredVariant]:
        """The variants of a key, with their bodies, oldest stored first. Empty when the key holds nothing.

        Variants a hard ban covers are left out, and those a soft ban covers come back ``stale``. The ban check is part
        of the lookup, never a second round trip.
        """

    @abstractmethod
    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        """The variant an entry id addresses, without its body."""

    @abstractmethod
    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> bool:
        """Store a variant in place of the one it supersedes (same key and variant) and of ``replaces``, if given.

        Nothing is stored, and ``False`` is returned, when a ban covers the key with a number above the stamp of the
        record: the fetch it comes from started before that invalidation. Nor when ``replaces`` is given and that
        variant is gone (purged, or replaced by another writer, possibly of another instance): the copy being written
        is older than what happened to it.
        The key then keeps at most ``keep`` variants: the oldest stored are deleted.
        """

    @abstractmethod
    async def counter(self) -> int:
        """The invalidation counter: the number of the last ban, ``0`` when there was none. What a fetch is stamped with."""

    @abstractmethod
    async def ban(self, kind: BanKind, prefix: str, mode: BanMode) -> Ban:
        """Append a ban to the log. It takes the next number of the counter, and is in force once this returns.

        The numbers are given in the order the bans commit, so that a counter read by a fetch has every lower ban
        visible. Bans do not delete the entries they cover: that is for :meth:`delete_key` and reclamation.
        """

    @abstractmethod
    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        """Delete the variant an entry id addresses. Tells whether there was one."""

    @abstractmethod
    async def delete_key(self, key: str) -> int:
        """Delete every variant of a key. Tells how many there were."""

    @abstractmethod
    async def delete_stored_before(self, cutoff: float, *, limit: int) -> int:
        """Delete at most ``limit`` variants last written before ``cutoff``. Tells how many were deleted."""

    @abstractmethod
    async def list_keys(
        self, *, endpoint: Optional[str] = None, after: Optional[str] = None, limit: int = 100
    ) -> list[str]:
        """The keys that hold a variant, by endpoint then key (bytewise), after the key ``after``, at most ``limit``."""

    @abstractmethod
    async def stats(self) -> list[EndpointStats]:
        """The counters of every endpoint that holds a variant, by endpoint."""

    @abstractmethod
    async def largest(self, *, endpoint: Optional[str] = None, limit: int = 10) -> list[VariantRecord]:
        """The variants with the largest bodies, largest first, of one endpoint or of all."""

    @abstractmethod
    async def count_refused(self, endpoint: str, count: int = 1) -> None:
        """Count responses of this endpoint that were not stored because their key was too long."""

    @abstractmethod
    async def body_digests(self) -> set[str]:
        """The digests of the stored bodies."""

    async def close(self) -> None:
        """Release what the backend holds."""
