from typing import Protocol

from harp.http import HttpRequest, HttpResponse


class IControllerResolver(Protocol):
    def resolve(self, request: HttpRequest): ...


class IAsyncController(Protocol):
    async def __call__(self, request: HttpRequest) -> HttpResponse: ...
