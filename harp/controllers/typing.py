from typing import Protocol

from harp.http import HttpRequest


class ControllerResolver(Protocol):
    async def resolve(self, request: HttpRequest): ...
