from collections.abc import Collection
from typing import Protocol

from hypercorn.typing import ASGIFramework

from harp.factories.proxy import Bind


class AdaptableFactory(Protocol):
    @property
    def binds(self) -> Collection[Bind]:
        return ...

    async def create(self) -> ASGIFramework:
        ...


class AbstractServerAdapter:
    def __init__(self, wrapped: AdaptableFactory):
        self.wrapped = wrapped

    async def serve(self):
        raise NotImplementedError()
