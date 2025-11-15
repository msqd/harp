from types import TracebackType
from typing import Optional, Self, Type

from httpx import AsyncBaseTransport, Request, Response
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)

logger = get_logger(__name__)


class AsyncFilterableTransport(AsyncBaseTransport):
    def __init__(self, transport: AsyncBaseTransport, dispatcher: IAsyncEventDispatcher):
        self._transport = transport
        self._dispatcher = dispatcher

    async def handle_async_request(self, request: Request) -> Response:
        event = HttpClientFilterEvent(request)
        await self._dispatcher.adispatch(EVENT_FILTER_HTTP_CLIENT_REQUEST, event)
        logger.debug(f"▶▶▶ {event.request}", headers=event.request.headers)
        if not event.response:
            event.response = await self._transport.handle_async_request(event.request)
        await self._dispatcher.adispatch(EVENT_FILTER_HTTP_CLIENT_RESPONSE, event)
        logger.debug(
            f"◀◀◀ {event.response}",
            cache_control=event.response.headers.get("cache-control"),
        )
        return event.response

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        await self.aclose()
