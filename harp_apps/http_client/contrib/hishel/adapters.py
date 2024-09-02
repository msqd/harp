import typing as tp
from datetime import datetime

import yaml
from hishel._async._storages import StoredResponse
from hishel._serializers import KNOWN_REQUEST_EXTENSIONS, KNOWN_RESPONSE_EXTENSIONS, Metadata
from hishel._utils import normalized_url
from httpcore import Request, Response

from harp.models import Blob
from harp_apps.http_client.contrib.hishel.utils import (
    prepare_headers_for_deserialization,
    prepare_headers_for_serialization,
)
from harp_apps.storage.types import IBlobStorage


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
    def __init__(self, storage: IBlobStorage):
        self.storage = storage

    async def store(self, key, /, *, response: Response, request: Request, metadata: Metadata) -> Blob:
        serialized_request = await self._serialize_request(request)
        serialized_response = await self._serialize_response(response)

        return await self._store_cache_meta(
            key,
            metadata=metadata,
            request=serialized_request,
            response=serialized_response,
        )

    async def retrieve(self, key: str) -> tp.Optional[StoredResponse]:
        # todo remove expired cache ?

        cached = await self.storage.get(key)
        if not cached:
            return None

        _metadata, _request, _response = await self._decode(cached)

        response = await self._unserialize_response(_response)
        request = await self._unserialize_request(_request)

        return (
            response,
            request,
            Metadata(
                cache_key=_metadata["cache_key"],
                created_at=datetime.strptime(_metadata["created_at"], "%a, %d %b %Y %H:%M:%S GMT"),
                number_of_uses=_metadata["number_of_uses"],
            ),
        )

    async def update_metadata_or_save(
        self, key: str, /, *, response: Response, request: Request, metadata: Metadata
    ) -> Blob:
        cached = await self.storage.get(key)
        if not cached:
            return await self.store(key, response=response, request=request, metadata=metadata)

        old_metadata, request_data, response_data = await self._decode(cached)
        await self._store_cache_meta(key, request=request_data, response=response_data, metadata=metadata)

    async def _decode(self, cached):
        cached = yaml.safe_load(cached.data.decode())
        request_data, response_data, raw_metadata = (
            cached["request"],
            cached["response"],
            cached["metadata"],
        )
        return raw_metadata, request_data, response_data

    async def _store_cache_meta(
        self,
        key,
        /,
        *,
        metadata: Metadata,
        request: SerializedRequest,
        response: SerializedResponse,
    ):
        # This is a special case where we don't want this to be content adressable. This is probably not very good, but
        # with hishel's current design, it's the only decent way to make it work that we found. Maybe we want to change
        # the key-value store in the future to be able to contain content addressable and unadressable data, even maybe
        # namespaced/typed data (although we hack "content-type to do it, for now).
        return await self.storage.put(
            Blob(
                id=key,
                data=yaml.safe_dump(
                    {
                        "request": request,
                        "response": response,
                        "metadata": {
                            "cache_key": metadata["cache_key"],
                            "number_of_uses": metadata["number_of_uses"],
                            "created_at": _ensure_datestring(metadata["created_at"]),
                        },
                    },
                    sort_keys=False,
                ).encode(),
                content_type="cache/meta",
            )
        )

    async def _serialize_request(self, request: Request) -> SerializedRequest:
        headers, varying_headers, metadata = prepare_headers_for_serialization(request.headers)
        headers = await self.storage.put(Blob.from_data(headers, content_type="http/headers"))
        return {
            "method": request.method.decode("ascii"),
            "url": normalized_url(request.url),
            "headers": headers.id,
            "varying": varying_headers,
            "extensions": {key: value for key, value in request.extensions.items() if key in KNOWN_REQUEST_EXTENSIONS},
        }

    async def _unserialize_request(self, data: SerializedRequest) -> Request:
        headers = await self.storage.get(data["headers"])

        return Request(
            method=data["method"],
            url=data["url"],
            headers=prepare_headers_for_deserialization(headers.data, varying=data.get("varying") or {}),
            extensions=data.get("extensions") or {},
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
        body = await self.storage.put(
            Blob.from_data(
                response.content,
                content_type=metadata.get("content-type") or "application/octet-stream",
            )
        )
        return {
            "status": response.status,
            "headers": headers.id,
            "varying": varying_headers,
            "body": body.id,
            "extensions": {
                key: value.decode("ascii")
                for key, value in response.extensions.items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        }

    async def _unserialize_response(self, data: SerializedResponse) -> Response:
        headers = await self.storage.get(data["headers"])
        body = await self.storage.get(data["body"])

        return Response(
            status=data["status"],
            headers=prepare_headers_for_deserialization(headers.data, varying=data.get("varying") or {}),
            content=body.data,
            extensions={key: value.encode() for key, value in (data.get("extensions") or {}).items()},
        )
