import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NamedTuple, Optional
from urllib.parse import urlsplit


def endpoint_of(key: str) -> str:
    """The endpoint a cache key belongs to: the key is the request url, its host replaced by the endpoint name."""
    return urlsplit(key).netloc


def digest_of(data: bytes) -> str:
    """The content digest bodies are stored under: sha256, in hexadecimal."""
    return hashlib.sha256(data).hexdigest()


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

    #: Reserved for the invalidation log (#1596): the invalidation counter read before the origin fetch. A ban check
    #: and the refusal of a stale fill compare against it. Nothing reads it yet, it is written as given (``0``).
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


class CacheRecords(ABC):
    """Where the cache keeps its records (ADR-0014): one per resource, one per variant, bodies by content digest.

    A body is shared by the records carrying it, and deleted with the last one. Counters per endpoint are kept as
    records are written and deleted. Every method is safe to run concurrently with the others.
    """

    @abstractmethod
    async def get_variants(self, key: str) -> list[StoredVariant]:
        """The variants of a key, with their bodies, oldest stored first. Empty when the key holds nothing."""

    @abstractmethod
    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        """The variant an entry id addresses, without its body."""

    @abstractmethod
    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> None:
        """Store a variant in place of the one it supersedes (same key and variant) and of ``replaces``, if given.

        The key then keeps at most ``keep`` variants: the oldest stored are deleted.
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
    async def body_digests(self) -> set[str]:
        """The digests of the stored bodies."""

    async def close(self) -> None:
        """Release what the backend holds."""
