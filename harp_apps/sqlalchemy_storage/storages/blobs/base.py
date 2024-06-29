from abc import ABCMeta

from harp_apps.sqlalchemy_storage.types import IBlobStorage


class AbstractBlobStorage(IBlobStorage, metaclass=ABCMeta):
    type = None
