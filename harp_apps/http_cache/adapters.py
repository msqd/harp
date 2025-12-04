import typing as tp
import uuid
import yaml
from datetime import datetime
from hishel import Entry, EntryMeta, Request, Response
from hishel._core.models import AnyIterable

from harp.models import Blob
from harp.utils.urls import _convert_url_to_string
from harp_apps.http_cache.utils import (
    deserialize_headers,
    prepare_headers_for_serialization,
)
from harp_apps.storage.types import IBlobStorage

# httpcore extension keys to preserve during serialization
# Migrated from hishel._serializers to avoid dependency on removed internal module
KNOWN_REQUEST_EXTENSIONS = ("timeout", "sni_hostname")
KNOWN_RESPONSE_EXTENSIONS = ("http_version", "reason_phrase")


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


def _ensure_datestring(date: datetime | str):
    if isinstance(date, datetime):
        date = date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return date


class AsyncStorageAdapter:
    """Adapter that serializes/deserializes Entry objects to/from HARP blob storage.

    This maintains backward compatibility with the YAML serialization format
    while adapting to hishel 1.0's Entry-based model.
    """

    def __init__(self, storage: IBlobStorage):
        self.storage = storage

    async def store_entry(self, key: str, entry: Entry) -> Blob:
        """Store an Entry object in blob storage.

        Args:
            key: The cache key
            entry: The Entry to store

        Returns:
            The stored Blob
        """
        serialized_request = await self._serialize_request(entry.request)
        serialized_response = await self._serialize_response(entry.response)

        return await self._store_entry_blob(
            key,
            entry_id=entry.id,
            request=serialized_request,
            response=serialized_response,
            meta=entry.meta,
            extra=entry.extra,
        )

    async def retrieve_entry(self, key: str) -> tp.Optional[Entry]:
        """Retrieve an Entry object from blob storage.

        Args:
            key: The cache key

        Returns:
            The Entry if found, None otherwise
        """
        cached = await self.storage.get(key)
        if not cached:
            return None

        entry_data = await self._decode(cached)

        response = await self._unserialize_response(entry_data["response"])
        request = await self._unserialize_request(entry_data["request"])

        # Parse metadata
        meta_data = entry_data["metadata"]
        meta = EntryMeta(
            created_at=meta_data.get(
                "created_at_ts",
                (
                    datetime.strptime(meta_data["created_at"], "%a, %d %b %Y %H:%M:%S GMT").timestamp()
                    if "created_at" in meta_data
                    else 0.0
                ),
            ),
            deleted_at=meta_data.get("deleted_at"),
        )

        # Parse entry ID (use stored UUID or generate from key for backward compat)
        entry_id_str = entry_data.get("id")
        if entry_id_str:
            entry_id = uuid.UUID(entry_id_str)
        else:
            # Backward compatibility: generate deterministic UUID from cache key
            entry_id = uuid.uuid5(uuid.NAMESPACE_URL, key)

        return Entry(
            id=entry_id,
            request=request,
            response=response,
            meta=meta,
            cache_key=key.encode("utf-8"),
            extra=entry_data.get("extra", {"number_of_uses": meta_data.get("number_of_uses", 0)}),
        )

    async def _decode(self, cached):
        """Decode cached blob data into structured format."""
        data = yaml.safe_load(cached.data.decode())
        return data

    async def _store_entry_blob(
        self,
        key: str,
        /,
        *,
        entry_id: uuid.UUID,
        request: SerializedRequest,
        response: SerializedResponse,
        meta: EntryMeta,
        extra: tp.Mapping[str, tp.Any],
    ):
        """Store entry data as a blob.

        This maintains the existing YAML format with added fields for hishel 1.0.
        """
        # Store both timestamp (new format) and formatted string (backward compat)
        created_at_dt = datetime.fromtimestamp(meta.created_at)

        return await self.storage.force_put(
            Blob(
                id=key,
                data=yaml.safe_dump(
                    {
                        "id": str(entry_id),  # Store UUID for hishel 1.0
                        "request": request,
                        "response": response,
                        "metadata": {
                            "cache_key": key,
                            "created_at": created_at_dt.strftime("%a, %d %b %Y %H:%M:%S GMT"),  # Backward compat
                            "created_at_ts": meta.created_at,  # New format
                            "deleted_at": meta.deleted_at,
                            "number_of_uses": extra.get("number_of_uses", 0),  # Backward compat
                        },
                        "extra": extra,  # Store full extra dict
                    },
                    sort_keys=False,
                ).encode(),
                content_type="cache/meta",
            ),
        )

    async def _serialize_request(self, request: Request) -> SerializedRequest:
        headers, varying_headers, metadata = prepare_headers_for_serialization(request.headers)
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
