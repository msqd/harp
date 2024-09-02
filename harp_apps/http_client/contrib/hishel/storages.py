import time
import typing as tp
from datetime import datetime, timezone

from hishel import AsyncBaseStorage
from hishel._async._storages import StoredResponse
from hishel._serializers import Metadata
from httpcore import Request, Response

from harp_apps.storage.types import IBlobStorage

from .adapters import AsyncStorageAdapter

HEADERS_ENCODING = "iso-8859-1"


class AsyncStorage(AsyncBaseStorage):
    def __init__(
        self,
        storage: IBlobStorage,
        ttl: tp.Optional[tp.Union[int, float]] = None,
        check_ttl_every: tp.Union[int, float] = 60,
    ):
        super().__init__(serializer=None, ttl=ttl)

        self._check_ttl_every = check_ttl_every
        self._last_cleaned = time.monotonic()
        self._impl = AsyncStorageAdapter(storage)
        self._storage = storage

    async def store(
        self,
        key: str,
        response: Response,
        request: Request,
        metadata: Metadata | None = None,
    ) -> None:
        # XXX this looks like the wrong place to do it, but hishel depends on this behaviour. Let's mimic the other
        #  storages, for now.
        metadata = metadata or Metadata(cache_key=key, created_at=datetime.now(timezone.utc), number_of_uses=0)

        await self._impl.store(
            key,
            request=request,
            response=response,
            metadata=metadata,
        )

    async def update_metadata(self, key: str, response: Response, request: Request, metadata: Metadata) -> None:
        await self._impl.update_metadata_or_save(
            key,
            request=request,
            response=response,
            metadata=metadata,
        )

    async def retrieve(self, key: str) -> tp.Optional[StoredResponse]:
        return await self._impl.retrieve(key)

    async def aclose(self) -> None:
        return
