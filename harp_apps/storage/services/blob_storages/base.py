from abc import ABCMeta

from harp_apps.storage.types import IBlobStorage


class AbstractBlobStorage(IBlobStorage, metaclass=ABCMeta):
    type = None
