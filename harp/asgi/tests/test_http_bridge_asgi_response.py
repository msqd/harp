"""A streamed response body crosses the ASGI bridge chunk by chunk, as it arrives."""

from httpx import AsyncByteStream

from harp.asgi.bridge.responses import HttpResponseAsgiBridge
from harp.http import HttpResponse


class ChunkedStream(AsyncByteStream):
    def __init__(self, *chunks: bytes, events: list):
        self.chunks = chunks
        self.events = events

    async def __aiter__(self):
        for chunk in self.chunks:
            self.events.append(("produced", chunk))
            yield chunk

    async def aclose(self):
        self.events.append(("closed",))


def recording_send(events: list):
    async def send(message):
        if message["type"] == "http.response.body":
            events.append(("sent", message["body"], message.get("more_body", False)))
        else:
            events.append(("start", message["status"]))

    return send


async def test_each_chunk_is_sent_before_the_next_one_is_read():
    events = []
    response = HttpResponse(b"")
    response.stream = ChunkedStream(b"one", b"two", events=events)

    await HttpResponseAsgiBridge(response, recording_send(events)).send()

    assert events == [
        ("start", 200),
        ("produced", b"one"),
        ("sent", b"one", True),
        ("produced", b"two"),
        ("sent", b"two", True),
        ("sent", b"", False),
        ("closed",),
    ]


async def test_the_stream_is_closed_when_the_client_goes_away():
    events = []
    response = HttpResponse(b"")
    response.stream = ChunkedStream(b"one", b"two", events=events)

    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("client disconnected")

    try:
        await HttpResponseAsgiBridge(response, send).send()
    except OSError:
        pass

    assert events[-1] == ("closed",)


async def test_the_stream_is_closed_when_the_client_is_gone_before_the_headers():
    events = []
    response = HttpResponse(b"")
    response.stream = ChunkedStream(b"one", events=events)

    async def send(message):
        raise OSError("client disconnected")

    try:
        await HttpResponseAsgiBridge(response, send).send()
    except OSError:
        pass

    assert events == [("closed",)]


async def test_an_in_memory_body_is_sent_in_one_message():
    events = []
    await HttpResponseAsgiBridge(HttpResponse(b"hello"), recording_send(events)).send()

    assert events == [("start", 200), ("sent", b"hello", False)]
