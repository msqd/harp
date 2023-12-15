from typing import Protocol

from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse


class IController(Protocol):
    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        ...
