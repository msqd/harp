import httpx
from whistle import AsyncEventDispatcher

from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_RESPONSE
from harp_apps.http_client.transports import AsyncFilterableTransport


class ClosableStream(httpx.AsyncByteStream):
    closed = False

    async def __aiter__(self):
        yield b"upstream"

    async def aclose(self):
        self.closed = True


async def test_a_replaced_upstream_response_is_closed():
    upstream = ClosableStream()
    dispatcher = AsyncEventDispatcher()

    async def replace(event):
        event.set_response(httpx.Response(503, content=b"replaced"))

    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, replace)
    transport = AsyncFilterableTransport(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=upstream)), dispatcher
    )

    response = await transport.handle_async_request(httpx.Request("GET", "http://upstream.local/"))

    assert response.status_code == 503
    assert upstream.closed
