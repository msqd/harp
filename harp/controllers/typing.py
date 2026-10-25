from typing import Optional, Protocol

from harp.http import HttpRequest, HttpResponse


class IControllerResolver(Protocol):
    async def resolve(self, request: HttpRequest): ...


class IAsyncController(Protocol):
    async def __call__(self, request: HttpRequest) -> HttpResponse: ...


class IEndpointSettings(Protocol):
    name: str
    port: Optional[int]


class IEndpoint(Protocol):
    settings: IEndpointSettings
