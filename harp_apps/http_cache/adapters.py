import time
import typing as tp
import uuid
import yaml
from datetime import UTC, datetime
from hishel import Entry, EntryMeta, Request, Response
from hishel._core.models import AnyIterable

from harp.models import Blob
from harp.models.redaction import Redaction
from harp.utils.urls import _convert_url_to_string
from harp_apps.http_cache.utils import (
    deserialize_headers,
    prepare_headers_for_serialization,
)
from harp_apps.storage.types import IBlobStorage

_Dumper = getattr(yaml, "CSafeDumper", yaml.SafeDumper)
_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# httpcore extension keys to preserve during serialization
# Migrated from hishel._serializers to avoid dependency on removed internal module
KNOWN_REQUEST_EXTENSIONS = ("timeout", "sni_hostname")
KNOWN_RESPONSE_EXTENSIONS = ("http_version", "reason_phrase")

# RFC 1123 wire format used for the backward-compatible `created_at` cache field. It is always UTC
# (the trailing "GMT" is literal), so it must be written and read as UTC regardless of the host
# timezone, otherwise the stored value is mislabeled and round-trips break across timezones.
_CREATED_AT_GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


def _format_created_at(timestamp: float) -> str:
    """Render a POSIX timestamp as an RFC 1123 GMT string."""
    return datetime.fromtimestamp(timestamp, UTC).strftime(_CREATED_AT_GMT_FORMAT)


def _parse_created_at(value: str) -> float:
    """Parse an RFC 1123 GMT string back to a POSIX timestamp."""
    return datetime.strptime(value, _CREATED_AT_GMT_FORMAT).replace(tzinfo=UTC).timestamp()


def stored_at_of(entry_data: tp.Mapping[str, tp.Any]) -> float:
    """When a decoded ``cache/meta`` blob was last written: stored, or freshened by a 304.

    Entries written before ``stored_at`` existed fall back to when they were created.
    """
    meta_data = entry_data["metadata"]
    if "stored_at" in meta_data:
        return meta_data["stored_at"]
    if "created_at_ts" in meta_data:
        return meta_data["created_at_ts"]
    return _parse_created_at(meta_data["created_at"]) if "created_at" in meta_data else 0.0


#: Top-level field of a ``cache/meta`` blob holding its variants, oldest first.
VARIANTS = "variants"


def variants_of(decoded: tp.Mapping[str, tp.Any]) -> list[dict[str, tp.Any]]:
    """The variants of a decoded ``cache/meta`` blob. One written before variants existed is a single entry."""
    return list(decoded[VARIANTS]) if VARIANTS in decoded else [dict(decoded)]


def variant_id(key: str, variant: tp.Mapping[str, tp.Any]) -> uuid.UUID:
    """The id of a stored variant, derived from its cache key when it was stored without one."""
    return uuid.UUID(variant["id"]) if variant.get("id") else uuid.uuid5(uuid.NAMESPACE_URL, key)


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


def _load_entry(raw: bytes) -> tp.Any:
    return yaml.load(raw.decode(), Loader=_Loader)


def _dump_entry(data: tp.Any) -> bytes:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False).encode()


class SerializedRequest(tp.TypedDict):
    method: str
    url: str
    headers: str
    varying: dict[str, str]
    extensions: dict[str, str]


class SerializedResponse(tp.TypedDict):
    status: int
    headers: str
    varying: dict[str, str]
    body: str
    extensions: dict[str, str]


class AsyncStorageAdapter:
    """Adapter that serializes/deserializes Entry objects to/from HARP blob storage.

    This maintains backward compatibility with the YAML serialization format
    while adapting to hishel 1.0's Entry-based model.
    """

    def __init__(self, storage: IBlobStorage):
        self.storage = storage

    async def serialize_variant(self, entry: Entry, redaction: tp.Optional[Redaction] = None) -> dict[str, tp.Any]:
        """Write the header and body blobs of an entry, and describe it as one variant of its cache key.

        Args:
            entry: The Entry to serialize
            redaction: Which request header values are replaced by the placeholder (the default set if omitted)

        Returns:
            The variant, ready for :meth:`write_variants`
        """
        return {
            "id": str(entry.id),  # Store UUID for hishel 1.0
            "request": await self._serialize_request(entry.request, redaction or Redaction()),
            "response": await self._serialize_response(entry.response),
            "selecting": selecting_headers(entry.request, entry.response),
            "metadata": {
                "cache_key": entry.cache_key.decode("utf-8") if entry.cache_key else None,
                # Store both timestamp (new format) and formatted string (backward compat)
                "created_at": _format_created_at(entry.meta.created_at),
                "created_at_ts": entry.meta.created_at,
                "deleted_at": entry.meta.deleted_at,
                "stored_at": time.time(),  # last write: what the storage ttl counts from
                "number_of_uses": entry.extra.get("number_of_uses", 0),  # Backward compat
            },
            "extra": dict(entry.extra),  # Store full extra dict
        }

    async def load_variants(self, key: str) -> list[dict[str, tp.Any]]:
        """The variants stored under a cache key, oldest first. Empty when the key holds nothing."""
        cached = await self.storage.get(key)
        return variants_of(_load_entry(cached.data)) if cached else []

    async def write_variants(self, key: str, variants: list[dict[str, tp.Any]]) -> None:
        """Replace what a cache key holds by these variants, or delete the key when there are none."""
        if not variants:
            await self.storage.delete(key)
            return
        await self.storage.force_put(
            Blob(id=key, data=_dump_entry({VARIANTS: variants}), content_type="cache/meta"),
        )

    async def unserialize_variant(self, key: str, data: tp.Mapping[str, tp.Any]) -> Entry:
        """Read a variant back into an Entry, raising ValueError when blobs it points at are missing."""
        response = await self._unserialize_response(data["response"])
        request = await self._unserialize_request(data["request"])

        # Parse metadata
        meta_data = data["metadata"]
        meta = EntryMeta(
            created_at=meta_data.get(
                "created_at_ts",
                (_parse_created_at(meta_data["created_at"]) if "created_at" in meta_data else 0.0),
            ),
            deleted_at=meta_data.get("deleted_at"),
        )

        return Entry(
            id=variant_id(key, data),
            request=request,
            response=response,
            meta=meta,
            cache_key=key.encode("utf-8"),
            extra={
                **data.get("extra", {"number_of_uses": meta_data.get("number_of_uses", 0)}),
                "stored_at": stored_at_of(data),
            },
        )

    async def _serialize_request(self, request: Request, redaction: Redaction) -> SerializedRequest:
        headers, varying_headers, metadata = prepare_headers_for_serialization(
            request.headers, redacted=redaction.headers
        )
        headers = await self.storage.put(Blob.from_data(headers, content_type="http/headers"))
        return {
            # hishel 1.0: method and url are already strings
            "method": (request.method if isinstance(request.method, str) else request.method.decode("ascii")),
            "url": (request.url if isinstance(request.url, str) else _convert_url_to_string(request.url)),
            "headers": headers.id,
            "varying": varying_headers,
            # hishel 1.0: metadata is dict, not extensions
            "extensions": {
                key: value
                for key, value in (request.metadata if hasattr(request, "metadata") else request.extensions).items()
                if key in KNOWN_REQUEST_EXTENSIONS
            },
        }

    async def _unserialize_request(self, data: SerializedRequest) -> Request:
        headers = await self.storage.get(data["headers"])

        # Handle case where headers blob is missing
        if headers is None:
            # Fallback to empty headers if the blob is missing
            headers_data = b""
        else:
            headers_data = headers.data

        return Request(
            method=data["method"],
            url=data["url"],
            headers=deserialize_headers(headers_data, varying=data.get("varying") or {}),
            # extensions=data.get("extensions") or {},
        )

    async def _serialize_response(self, response: Response) -> SerializedResponse:
        headers, varying_headers, metadata = prepare_headers_for_serialization(
            response.headers,
            varying=(
                b"date",
                b"content-length",
            ),
        )
        headers = await self.storage.put(Blob.from_data(headers, content_type="http/headers"))

        # hishel 1.0: Entry.response is hishel Response with stream, not httpcore Response
        # Check if it has content (httpcore) or needs to be read (hishel)
        if hasattr(response, "content"):
            # httpcore Response
            content = response.content
            status = response.status
            extensions = response.extensions
        else:
            # hishel Response
            content = await response.aread()
            status = response.status_code
            extensions = response.metadata

        body = await self.storage.put(
            Blob.from_data(
                content,
                content_type=metadata.get("content-type") or "application/octet-stream",
            )
        )
        return {
            "status": status,
            "headers": headers.id,
            "varying": varying_headers,
            "body": body.id,
            "extensions": {
                key: value.decode("ascii") if isinstance(value, bytes) else value
                for key, value in extensions.items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        }

    async def _unserialize_response(self, data: SerializedResponse) -> tp.Optional[Response]:
        headers = await self.storage.get(data["headers"])
        body = await self.storage.get(data["body"])

        # Handle case where blobs are missing (storage failure or cache corruption)
        if headers is None or body is None:
            # Log which blobs are missing for debugging
            missing = []
            if headers is None:
                missing.append(f"headers (id={data['headers']})")
            if body is None:
                missing.append(f"body (id={data['body']})")
            raise ValueError(
                f"Cache entry incomplete, missing blob(s): {', '.join(missing)}. "
                "This may indicate storage corruption or a previous partial write."
            )

        return Response(
            status_code=data["status"],
            headers=deserialize_headers(headers.data, varying=data.get("varying") or {}),
            stream=AnyIterable(body.data),
            metadata={
                key: value.encode() if isinstance(value, str) else value
                for key, value in (data.get("extensions") or {}).items()
            },
        )
