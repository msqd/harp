import asyncio
import gzip

import httpx
import pytest

from harp_apps.http_client.aiohttp_transport import AiohttpTransport


class RawServer:
    """A server answering every request with canned bytes, recording the raw requests and connections."""

    def __init__(
        self, reply: bytes = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok", *, delay: float = 0, close: bool = False
    ):
        self.reply = reply
        self.delay = delay
        self.close = close
        self.requests: list[bytes] = []
        self.connections = 0
        self._writers = []

    async def _handle(self, reader, writer):
        self.connections += 1
        self._writers.append(writer)
        try:
            while data := await reader.readuntil(b"\r\n\r\n"):
                head = data
                length = 0
                for line in head.lower().split(b"\r\n"):
                    if line.startswith(b"content-length:"):
                        length = int(line.split(b":")[1])
                self.requests.append(head + (await reader.readexactly(length) if length else b""))
                if self.delay:
                    await asyncio.sleep(self.delay)
                writer.write(self.reply)
                await writer.drain()
                if self.close or not self.reply:
                    break
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()

    async def __aenter__(self):
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.url = f"http://127.0.0.1:{self._server.sockets[0].getsockname()[1]}"
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        for writer in self._writers:
            writer.close()
        await self._server.wait_closed()


@pytest.fixture
async def transport():
    transport = AiohttpTransport()
    yield transport
    await transport.aclose()


async def send(transport, request):
    response = await transport.handle_async_request(request)
    await response.aread()
    await response.aclose()
    return response


async def test_status_reason_and_body(transport):
    reply = b"HTTP/1.1 418 I'm a teapot\r\nContent-Length: 4\r\n\r\ntea!"
    async with RawServer(reply) as server:
        response = await send(transport, httpx.Request("GET", server.url))
    assert (response.status_code, response.reason_phrase, response.content) == (418, "I'm a teapot", b"tea!")


async def test_response_headers_keep_order_and_duplicates(transport):
    reply = b"HTTP/1.1 200 OK\r\nX-B: 1\r\nSet-Cookie: a=1\r\nX-A: 2\r\nSet-Cookie: b=2\r\nContent-Length: 0\r\n\r\n"
    async with RawServer(reply) as server:
        response = await send(transport, httpx.Request("GET", server.url))
    assert response.headers.raw == [
        (b"X-B", b"1"),
        (b"Set-Cookie", b"a=1"),
        (b"X-A", b"2"),
        (b"Set-Cookie", b"b=2"),
        (b"Content-Length", b"0"),
    ]


async def test_request_is_sent_as_given(transport):
    headers = [("host", "stub"), ("x-b", "1"), ("x-a", "2"), ("x-b", "3")]
    async with RawServer() as server:
        await send(transport, httpx.Request("POST", server.url + "/path?q=1", headers=headers, content=b"payload"))
    head, _, body = server.requests[0].partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0] == b"POST /path?q=1 HTTP/1.1"
    assert lines[1:] == [b"host: stub", b"x-b: 1", b"x-a: 2", b"x-b: 3", b"Content-Length: 7"]
    assert body == b"payload"


async def test_no_header_is_added_on_its_own(transport):
    async with RawServer() as server:
        await send(transport, httpx.Request("GET", server.url, headers=[("host", "stub")]))
    names = {line.split(b":")[0].lower() for line in server.requests[0].split(b"\r\n")[1:] if line}
    assert names == {b"host"}


async def test_redirects_are_not_followed(transport):
    reply = b"HTTP/1.1 302 Found\r\nLocation: /elsewhere\r\nContent-Length: 0\r\n\r\n"
    async with RawServer(reply) as server:
        response = await send(transport, httpx.Request("GET", server.url))
    assert (response.status_code, response.headers["location"]) == (302, "/elsewhere")
    assert len(server.requests) == 1


async def test_content_encoding_is_left_to_httpx(transport):
    body = gzip.compress(b"hello hello hello")
    reply = b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: %d\r\n\r\n" % len(body) + body
    async with RawServer(reply) as server:
        response = await send(transport, httpx.Request("GET", server.url))
    assert response.headers["content-encoding"] == "gzip"
    assert response.content == b"hello hello hello"


async def test_connections_are_kept_alive(transport):
    async with RawServer() as server:
        for _ in range(3):
            await send(transport, httpx.Request("GET", server.url))
    assert (len(server.requests), server.connections) == (3, 1)


async def test_connection_refused_is_a_connect_error(transport):
    with pytest.raises(httpx.ConnectError):
        await send(transport, httpx.Request("GET", "http://127.0.0.1:1"))


async def test_read_timeout(transport):
    async with RawServer(delay=1) as server:
        request = httpx.Request("GET", server.url, extensions={"timeout": {"read": 0.1, "connect": 1}})
        with pytest.raises(httpx.ReadTimeout):
            await send(transport, request)


async def test_server_closing_without_answer_is_a_remote_protocol_error(transport):
    async with RawServer(b"") as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, httpx.Request("GET", server.url))


async def test_garbage_answer_is_a_remote_protocol_error(transport):
    async with RawServer(b"not http at all\r\n\r\n") as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, httpx.Request("GET", server.url))


async def test_body_cut_short_is_a_remote_protocol_error(transport):
    async with RawServer(b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nabc", close=True) as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, httpx.Request("GET", server.url))


def test_retries_are_not_supported():
    with pytest.raises(ValueError, match="retries"):
        AiohttpTransport(retries=1)
