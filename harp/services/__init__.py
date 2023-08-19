import rodi

from harp.services.storage import Storage
from harp.services.storage.in_memory import InMemoryDatabase, InMemoryStorage

container = rodi.Container()
container.add_exact_singleton(InMemoryDatabase)
container.add_singleton(Storage, InMemoryStorage)

__all__ = ["container"]
