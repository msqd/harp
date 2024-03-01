from typing import Protocol

from harp.asgi import ASGIResponse
from harp.http import HttpRequest


class Controller(Protocol):
    async def __call__(self, request: HttpRequest, response: ASGIResponse):
        ...
