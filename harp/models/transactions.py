import dataclasses
from datetime import datetime
from enum import StrEnum
from typing import List

from .base import Entity
from .messages import Message
from .redaction import Redaction


def encode_markers(markers) -> str | None:
    """Encode transaction markers for the ``markers`` storage column (sorted, comma separated)."""
    return ",".join(sorted(markers)) or None


def decode_markers(value: str | None) -> set:
    """Decode the ``markers`` storage column back to a set."""
    return set(value.split(",")) if value else set()


def encode_cache_flag(cached) -> str | None:
    """Encode a transaction cache-hit flag for the ``x_cached`` storage column.

    A truthy flag is stored as the string ``"true"``; anything else as ``None``.

    The flag comes from the cache itself, through the ``hishel_from_cache`` response extension, not
    from the ``X-Cache`` header. HARP emits that header for clients, but an upstream may emit one of
    its own, so it cannot be read back as evidence of a HARP cache hit.
    """
    return "true" if cached else None


class CacheOutcome(StrEnum):
    """What the cache did for a response, as the cache itself reports it (hishel and the store, no rule of ours)."""

    #: Served from the cache, fresh.
    HIT = "hit"

    #: Served from the cache as it was, though no longer fresh (the operator allows it).
    STALE = "stale"

    #: Stored response confirmed by the origin (``304``), then served.
    REVALIDATED = "revalidated"

    #: Fetched from the origin, and kept when it can be (a response that replaced a stale one is a miss too).
    MISS = "miss"

    #: Fetched from the origin, and not kept: the exchange or its response forbids storage, or the method is not cached.
    UNCACHEABLE = "uncacheable"


#: The extras of a transaction describing its cache outcome, and the ``x_`` column each is stored in.
CACHE_EXTRAS = {
    "cache_outcome": "x_cache_outcome",
    "cache_key": "x_cache_key",
    "cache_variant": "x_cache_variant",
    "cache_seq": "x_cache_seq",
    "cache_age": "x_cache_age",
    "cache_ttl": "x_cache_ttl",
}


def cache_columns(extras: dict) -> dict:
    """The ``x_`` columns for the cache extras of a transaction (``None`` for what the cache did not report)."""
    return {column: extras.get(name) for name, column in CACHE_EXTRAS.items()}


@dataclasses.dataclass(kw_only=True)
class Transaction(Entity):
    """An HTTP transaction, as stored and as sent to the dashboard."""

    id: str = None
    """Unique identifier for this transaction."""

    type: str  # enum http websocket lifecycle ...
    """Type of ASGI transaction: http, websocket, lifecycle, ..."""

    endpoint: str = None
    """Endpoint name, if any (this describes which proxy controller handled the request)."""

    started_at: datetime
    """Timestamp of the transaction start."""

    finished_at: datetime = None
    """Timestamp of the transaction end (if it has ended), or None."""

    # Computed fields

    elapsed: float = None
    """Elapsed time in seconds, if the transaction has ended."""

    tpdex: int = None
    """TPDEX score, if the transaction has ended."""

    # Relations

    messages: List[Message] = None
    tags: dict = dataclasses.field(default_factory=dict)

    # Extra attributes
    extras: dict = dataclasses.field(default_factory=dict)

    # Markers, used for transaction management (e.g. skip storage on high pressure)
    markers: set = dataclasses.field(default_factory=set)

    # Which header and query parameter values are replaced by a placeholder before anything is stored
    redaction: Redaction = dataclasses.field(default_factory=Redaction)

    @classmethod
    def _get_fields(cls, base_fields=True):
        """Redaction rules are working state: kept out of the serialised form (dict and schema)."""
        return [f for f in super()._get_fields(base_fields) if f.field.name != "redaction"]

    def as_storable_dict(self, /, *, with_messages=False, with_tags=False):
        """Create a dict that can be passed to a storage creation method."""
        data = self._asdict()

        if not with_messages:
            data.pop("messages", None)

        if not with_tags:
            data.pop("tags", None)

        extras = data.pop("extras", {})

        data["markers"] = encode_markers(self.markers)
        data["x_cached"] = encode_cache_flag(extras.get("cached"))
        data.update(cache_columns(extras))
        data["x_method"] = extras.get("method")
        data["x_no_cache"] = bool(extras.get("no_cache"))
        data["x_status_class"] = extras.get("status_class")

        return data

    def _asdict(self, /, *, secure=True):
        result = dataclasses.asdict(self)
        result.pop("redaction", None)
        result["markers"] = sorted(self.markers)
        return result
