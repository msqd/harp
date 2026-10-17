import pytest

from harp.asgi.bridge.streams import AsyncStreamFromAsgiReceive
from harp.http import ClientDisconnected


def _receive(*messages):
    queue = list(messages)

    async def receive():
        return queue.pop(0)

    return receive


async def test_complete_body_is_yielded():
    stream = AsyncStreamFromAsgiReceive(
        _receive(
            {"type": "http.request", "body": b"ab", "more_body": True},
            {"type": "http.request", "body": b"cd", "more_body": False},
        )
    )
    assert b"".join([part async for part in stream]) == b"abcd"


async def test_disconnect_before_end_of_body_raises():
    stream = AsyncStreamFromAsgiReceive(
        _receive({"type": "http.request", "body": b"ab", "more_body": True}, {"type": "http.disconnect"})
    )
    with pytest.raises(ClientDisconnected):
        [part async for part in stream]
