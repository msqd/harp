from typing import Protocol

from harp.core.asgi.messages import ASGIRequest, ASGIResponse


class IController(Protocol):
    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        ...
