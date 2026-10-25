"""Bounded response streaming: the client gets the upstream body as it arrives, HARP records at most a capped prefix."""

import asyncio
import gzip

import httpx
import pytest
import respx

from harp.http import HttpRequest, HttpResponse
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import (
    EVENT_FILTER_PROXY_RESPONSE,
    EVENT_PROXY_ERROR,
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
)
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.constants import CLIENT_DISCONNECTED, TRUNCATED_RESPONSE_BODY

BASE_URL = "http://example.com"


class RecordingDispatcher:
    """Keeps the events a controller dispatches, in order."""

    def __init__(self, on_event=None):
        self.events = []
        self.on_event = on_event

    async def adispatch(self, event_id, event=None):
        self.events.append((event_id, event))
        if self.on_event:
            await self.on_event(event_id, event)
        return event

    def ids(self):
        return [event_id for event_id, _ in self.events]

    def recorded_response(self) -> HttpResponse:
        (message,) = [
            event.message
            for event_id, event in self.events
            if event_id == EVENT_TRANSACTION_MESSAGE and event.message.kind == "response"
        ]
        return message


def create_controller(dispatcher, **kwargs):
    remote = Remote.from_settings_dict({"endpoints": [{"url": BASE_URL}]})
    return HttpProxyController(remote, http_client=httpx.AsyncClient(), dispatcher=dispatcher, name="api", **kwargs)


async def read_all(response: HttpResponse) -> bytes:
    return b"".join([chunk async for chunk in response.stream])


@respx.mock
async def test_first_chunk_reaches_the_client_before_the_upstream_sends_the_next():
    second_chunk_allowed = asyncio.Event()

    async def upstream_body():
        yield b"first"
        await second_chunk_allowed.wait()
        yield b"second"

    respx.get(BASE_URL).mock(side_effect=lambda request: httpx.Response(200, content=upstream_body()))
    controller = create_controller(RecordingDispatcher())

    response = await asyncio.wait_for(controller(HttpRequest()), timeout=1)
    chunks = aiter(response.stream)

    assert await asyncio.wait_for(anext(chunks), timeout=1) == b"first"
    second_chunk_allowed.set()
    assert b"".join([chunk async for chunk in chunks]) == b"second"


@respx.mock
async def test_transaction_ends_once_the_body_is_sent():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=b"hello"))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)

    response = await controller(HttpRequest())
    assert EVENT_TRANSACTION_ENDED not in dispatcher.ids()

    assert await read_all(response) == b"hello"
    assert dispatcher.ids()[-1] == EVENT_TRANSACTION_ENDED


@respx.mock
async def test_body_under_the_cap_is_recorded_whole():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=b"0123456789"))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher, max_recorded_body_size=10)

    response = await controller(HttpRequest())
    await read_all(response)

    recorded = dispatcher.recorded_response()
    await recorded.aread()
    assert recorded.body == b"0123456789"
    (_, ended) = dispatcher.events[-1]
    assert TRUNCATED_RESPONSE_BODY not in ended.transaction.markers


@respx.mock
async def test_body_over_the_cap_is_streamed_whole_and_recorded_truncated():
    async def upstream_body():
        for chunk in (b"0123", b"4567", b"89ab"):
            yield chunk

    respx.get(BASE_URL).mock(side_effect=lambda request: httpx.Response(200, content=upstream_body()))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher, max_recorded_body_size=6)

    response = await controller(HttpRequest())

    assert await read_all(response) == b"0123456789ab"
    recorded = dispatcher.recorded_response()
    await recorded.aread()
    assert recorded.body == b"012345"
    assert recorded.status == 200
    (_, ended) = dispatcher.events[-1]
    assert TRUNCATED_RESPONSE_BODY in ended.transaction.markers


@respx.mock
async def test_recording_cap_defaults_to_one_mebibyte():
    body = b"x" * (1024 * 1024 + 1)
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=body))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)

    response = await controller(HttpRequest())

    assert await read_all(response) == body
    recorded = dispatcher.recorded_response()
    await recorded.aread()
    assert len(recorded.body) == 1024 * 1024


@respx.mock
async def test_upstream_failing_mid_body_ends_the_transaction_as_an_error():
    async def upstream_body():
        yield b"partial"
        raise httpx.ReadError("connection reset")

    respx.get(BASE_URL).mock(side_effect=lambda request: httpx.Response(200, content=upstream_body()))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)

    response = await controller(HttpRequest())

    with pytest.raises(httpx.ReadError):
        await read_all(response)
    assert EVENT_PROXY_ERROR in dispatcher.ids()
    (_, ended) = dispatcher.events[-1]
    assert ended.transaction.extras["status_class"] == "ERR"


@respx.mock
async def test_upstream_response_replaced_by_a_filter_is_closed():
    closed = asyncio.Event()

    class UpstreamBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"upstream"

        async def aclose(self):
            closed.set()

    async def replace_response(event_id, event):
        if event_id == EVENT_FILTER_PROXY_RESPONSE:
            event.set_response(HttpResponse(b"replaced"))

    respx.get(BASE_URL).mock(side_effect=lambda request: httpx.Response(200, stream=UpstreamBody()))
    controller = create_controller(RecordingDispatcher(on_event=replace_response))

    response = await controller(HttpRequest())

    assert await read_all(response) == b"replaced"
    assert closed.is_set()


@respx.mock
async def test_a_filter_reading_the_body_leaves_it_whole_for_the_client_and_the_record():
    async def read_body(event_id, event):
        if event_id == EVENT_FILTER_PROXY_RESPONSE:
            assert await event.response.aread() == b"0123456789"

    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=b"0123456789"))
    dispatcher = RecordingDispatcher(on_event=read_body)
    controller = create_controller(dispatcher, max_recorded_body_size=4)

    response = await controller(HttpRequest())

    assert await read_all(response) == b"0123456789"
    recorded = dispatcher.recorded_response()
    assert await recorded.aread() == b"0123"


@respx.mock
async def test_a_compressed_body_is_decoded_in_bounded_steps():
    bomb = gzip.compress(b"0" * 32 * 1024 * 1024)
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, headers={"content-encoding": "gzip"}, content=bomb))
    controller = create_controller(RecordingDispatcher(), max_recorded_body_size=1024)

    response = await controller(HttpRequest())
    size = largest = 0
    async for chunk in response.stream:
        size += len(chunk)
        largest = max(largest, len(chunk))

    assert size == 32 * 1024 * 1024
    assert largest <= 256 * 1024


async def send_through_asgi(response: HttpResponse) -> list:
    from harp.asgi.bridge.responses import HttpResponseAsgiBridge

    messages = []

    async def send(message):
        messages.append(message)

    await HttpResponseAsgiBridge(response, send).send()
    return messages


@pytest.mark.parametrize(
    "method, status",
    [("GET", 204), ("GET", 304), ("HEAD", 200)],
    ids=["204", "304", "HEAD"],
)
@respx.mock
async def test_a_response_without_a_body_ends_the_transaction(method, status):
    respx.route(method=method, url=BASE_URL).mock(return_value=httpx.Response(status))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)

    await send_through_asgi(await controller(HttpRequest(method=method)))

    assert dispatcher.ids()[-1] == EVENT_TRANSACTION_ENDED


@respx.mock
async def test_a_filter_leaving_the_body_unread_still_ends_the_transaction():
    async def mark(event_id, event):
        if event_id == EVENT_FILTER_PROXY_RESPONSE:
            event.transaction.markers.add("seen")

    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=b"hello"))
    dispatcher = RecordingDispatcher(on_event=mark)
    controller = create_controller(dispatcher)

    messages = await send_through_asgi(await controller(HttpRequest()))

    assert b"".join(message.get("body", b"") for message in messages) == b"hello"
    assert dispatcher.ids()[-1] == EVENT_TRANSACTION_ENDED


@respx.mock
async def test_client_leaving_mid_body_is_marked_and_the_body_read_so_far_is_recorded():
    async def upstream_body():
        for chunk in (b"first", b"second", b"third"):
            yield chunk

    respx.get(BASE_URL).mock(side_effect=lambda request: httpx.Response(200, content=upstream_body()))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)
    response = await controller(HttpRequest())

    sent = []

    async def send(message):
        if message.get("body"):
            if sent:
                raise OSError("client disconnected")
            sent.append(message["body"])

    from harp.asgi.bridge.responses import HttpResponseAsgiBridge

    with pytest.raises(OSError):
        await HttpResponseAsgiBridge(response, send).send()

    (_, ended) = dispatcher.events[-1]
    assert CLIENT_DISCONNECTED in ended.transaction.markers
    recorded = dispatcher.recorded_response()
    assert await recorded.aread() == b"firstsecond"


@respx.mock
async def test_client_reading_the_whole_body_is_not_marked_as_disconnected():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=b"hello"))
    dispatcher = RecordingDispatcher()
    controller = create_controller(dispatcher)

    await send_through_asgi(await controller(HttpRequest()))

    (_, ended) = dispatcher.events[-1]
    assert CLIENT_DISCONNECTED not in ended.transaction.markers
