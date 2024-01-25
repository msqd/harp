from typing import Protocol

from harp.asgi import ASGIRequest, ASGIResponse


class Controller(Protocol):
    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        ...
