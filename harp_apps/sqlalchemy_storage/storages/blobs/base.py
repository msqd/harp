from abc import ABCMeta, abstractmethod

from harp.models import Blob
from harp_apps.sqlalchemy_storage.types import BlobStorage


class AbstractBlobStorage(BlobStorage, metaclass=ABCMeta):
    type = None

    @abstractmethod
    async def get(self, blob_id: str):
        raise NotImplementedError

    @abstractmethod
    async def put(self, blob: Blob):
        raise NotImplementedError

    @abstractmethod
    async def delete(self, blob_id: str):
        raise NotImplementedError

    @abstractmethod
    async def exists(self, blob_id: str) -> bool:
        raise NotImplementedError
