"""Entries, as the records the cache stores them in (ADR-0014), and back.

An entry is split into a :class:`~harp_apps.http_cache.records.VariantRecord` (what is queried: key, variant, status,
sizes, instants), a body (stored by content digest) and a head (the request and response heads, which are only ever read
back whole).
"""

import hashlib
import json
import time
import typing as tp

from hishel import Entry, EntryMeta, Request, Response
from hishel._core.models import AnyIterable

from harp.models.redaction import Redaction
from harp_apps.http_cache.records import StoredVariant, VariantRecord, digest_of, endpoint_of
from harp_apps.http_cache.utils import deserialize_headers, prepare_headers_for_serialization

# httpcore extension keys to preserve during serialization
# Migrated from hishel._serializers to avoid dependency on removed internal module
KNOWN_RESPONSE_EXTENSIONS = ("http_version", "reason_phrase")

#: Header bytes are kept as text one to one, whatever their encoding: the head is JSON, and headers need not be UTF-8.
_HEADERS_ENCODING = "latin-1"


def selecting_headers(request: Request, response: Response) -> dict[str, tp.Optional[str]]:
    """The values of the request headers the response varies on: what makes it one variant among others.

    Two exchanges with equal selecting headers are the same variant, whichever was stored last wins. ``Vary: *``
    cannot be told apart by headers, so it is one variant of its own.
    """
    names = sorted(
        {name.strip().lower() for value in response.headers.get_list("vary") or [] for name in value.split(",")} - {""}
    )
    if "*" in names:
        return {"*": None}
    return {name: request.headers.get(name) for name in names}


def variant_of(selecting: tp.Mapping[str, tp.Optional[str]]) -> str:
    """Identifies a combination of selecting header values: empty when the response does not vary."""
    if not selecting:
        return ""
    return hashlib.sha256(json.dumps(selecting, sort_keys=True).encode()).hexdigest()


async def to_record(
    entry: Entry, redaction: tp.Optional[Redaction] = None, *, stamp: int = 0
) -> tuple[VariantRecord, bytes]:
    """Describe an entry as one variant of its cache key, with its body (which this reads to the end).

    Args:
        entry: The Entry to describe
        redaction: Which request header values are replaced by the placeholder (the default set if omitted)
        stamp: The invalidation counter read before the origin fetch, reserved for the invalidation log (#1596)
    """
    redaction = redaction or Redaction()
    body = await entry.response.aread()
    request, response = entry.request, entry.response
    request_headers, request_varying, _ = prepare_headers_for_serialization(request.headers, redacted=redaction.headers)
    response_headers, response_varying, _ = prepare_headers_for_serialization(
        response.headers, varying=(b"date", b"content-length")
    )
    selecting = selecting_headers(request, response)
    head = {
        "request": {
            "method": request.method,
            "url": request.url,
            "headers": request_headers.decode(_HEADERS_ENCODING),
            "varying": request_varying,
        },
        "response": {
            "headers": response_headers.decode(_HEADERS_ENCODING),
            "varying": response_varying,
            "extensions": {
                key: value.decode("ascii") if isinstance(value, bytes) else value
                for key, value in response.metadata.items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        },
        "selecting": selecting,
        "deleted_at": entry.meta.deleted_at,
        "extra": {key: value for key, value in entry.extra.items() if key != "stored_at"},
    }
    key = entry.cache_key.decode("utf-8")
    record = VariantRecord(
        key=key,
        variant=variant_of(selecting),
        entry_id=entry.id,
        endpoint=endpoint_of(key),
        stamp=stamp,
        status=response.status_code,
        vary=", ".join(selecting) or None,
        body_digest=digest_of(body),
        body_size=len(body),
        created_at=entry.meta.created_at,
        stored_at=time.time(),  # last write: what the storage ttl counts from
        head=json.dumps(head, separators=(",", ":")).encode(),
    )
    return record, body


def to_entry(stored: StoredVariant) -> Entry:
    """Read a stored variant back into an Entry."""
    record, body = stored
    head = json.loads(record.head)
    sent, received = head["request"], head["response"]
    return Entry(
        id=record.entry_id,
        request=Request(
            method=sent["method"],
            url=sent["url"],
            headers=deserialize_headers(sent["headers"].encode(_HEADERS_ENCODING), varying=sent["varying"]),
        ),
        response=Response(
            status_code=record.status,
            headers=deserialize_headers(received["headers"].encode(_HEADERS_ENCODING), varying=received["varying"]),
            stream=AnyIterable(body),
            metadata={
                key: value.encode() if isinstance(value, str) else value
                for key, value in received["extensions"].items()
            },
        ),
        meta=EntryMeta(created_at=record.created_at, deleted_at=head["deleted_at"]),
        cache_key=record.key.encode("utf-8"),
        extra={**head["extra"], "stored_at": record.stored_at},
    )
