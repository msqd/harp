"""
What HARP relies on from the httpx transport under its client, checked against a raw local server.

Every transport in `TRANSPORT_TYPES` runs the same tests, stock `httpx.AsyncHTTPTransport` included as the reference.
What a transport cannot honour is listed in `KNOWN_DIVERGENCES` (a strict xfail with the reason), never skipped.
"""

import asyncio
import gzip
import socket
import ssl
import struct
import subprocess

import httpx
import pytest

from harp_apps.http_client.tests.transports import TRANSPORT_TYPES, transport_class

AIOHTTP = "harp_apps.http_client.aiohttp_transport.AiohttpTransport"

#: (test name, transport type) -> why the transport cannot pass.
KNOWN_DIVERGENCES: dict[tuple[str, str], str] = {}

OK = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


class RawServer:
    """
    Answers every request with the next reply (the last one repeats), as canned bytes. It records the raw requests, the
    connections opened and the most requests in flight at once.
    """

    def __init__(self, *replies: bytes, delay: float = 0, close: bool = False, reset: bool = False, ssl_context=None):
        self.replies = list(replies) or [OK]
        self.delay = delay
        self.close = close
        self.reset = reset
        self.ssl_context = ssl_context
        self.requests: list[bytes] = []
        self.connections = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self._writers: list = []

    async def _read_request(self, reader) -> bytes:
        head = await reader.readuntil(b"\r\n\r\n")
        lowered = head.lower()
        if b"transfer-encoding: chunked" in lowered:
            body = b""
            while True:
                size = int((await reader.readuntil(b"\r\n")).strip(), 16)
                if size == 0:
                    await reader.readuntil(b"\r\n")
                    break
                body += await reader.readexactly(size + 2)
            return head + body
        length = 0
        for line in lowered.split(b"\r\n"):
            if line.startswith(b"content-length:"):
                length = int(line.split(b":")[1])
        return head + (await reader.readexactly(length) if length else b"")

    async def _handle(self, reader, writer):
        self.connections += 1
        self._writers.append(writer)
        try:
            while True:
                self.requests.append(await self._read_request(reader))
                self.in_flight += 1
                self.max_in_flight = max(self.max_in_flight, self.in_flight)
                try:
                    if self.delay:
                        await asyncio.sleep(self.delay)
                    if self.reset:
                        sock = writer.get_extra_info("socket")
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                        break
                    reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
                    writer.write(reply)
                    await writer.drain()
                finally:
                    self.in_flight -= 1
                if self.close or not reply:
                    break
        except (asyncio.IncompleteReadError, ConnectionError, ssl.SSLError):
            pass
        finally:
            writer.close()

    async def __aenter__(self):
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0, ssl=self.ssl_context)
        scheme = "https" if self.ssl_context else "http"
        self.url = f"{scheme}://127.0.0.1:{self._server.sockets[0].getsockname()[1]}"
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        for writer in self._writers:
            writer.transport.abort()  # no TLS shutdown handshake to wait for
        await self._server.wait_closed()


@pytest.fixture(params=TRANSPORT_TYPES)
def transport_type(request):
    reason = KNOWN_DIVERGENCES.get((request.node.originalname, request.param))
    if reason:
        request.applymarker(pytest.mark.xfail(reason=reason, strict=True))
    return request.param


@pytest.fixture
async def make_transport(transport_type):
    transports = []

    def make(**arguments):
        transports.append(transport_class(transport_type)(**arguments))
        return transports[-1]

    yield make
    for transport in transports:
        await transport.aclose()


@pytest.fixture
def transport(make_transport):
    return make_transport()


async def send(transport, request) -> tuple[httpx.Response, bytes]:
    """The response and its body as the transport delivered it (not decoded)."""
    response = await transport.handle_async_request(request)
    raw = b"".join([chunk async for chunk in response.aiter_raw()])
    await response.aclose()
    return response, raw


def get(url, **kwargs):
    return httpx.Request("GET", url, **kwargs)


# --- what goes out ---------------------------------------------------------------------------------------------------


async def test_request_line_headers_and_body_are_sent_as_given(transport):
    headers = [("host", "stub"), ("X-B", "1"), ("x-a", "2"), ("X-B", "3"), ("X-Mixed-Case", "v")]
    async with RawServer() as server:
        await send(transport, httpx.Request("POST", server.url + "/path?q=1", headers=headers, content=b"payload"))
    head, _, body = server.requests[0].partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0] == b"POST /path?q=1 HTTP/1.1"
    assert lines[1:] == [b"host: stub", b"X-B: 1", b"x-a: 2", b"X-B: 3", b"X-Mixed-Case: v", b"Content-Length: 7"]
    assert body == b"payload"


async def test_no_header_is_added_on_its_own(transport):
    async with RawServer() as server:
        await send(transport, get(server.url, headers=[("host", "stub")]))
    names = {line.split(b":")[0].lower() for line in server.requests[0].split(b"\r\n")[1:] if line}
    assert names == {b"host"}


async def test_request_without_body_has_none(transport):
    async with RawServer() as server:
        await send(transport, get(server.url, headers=[("host", "stub")]))
    assert server.requests[0].endswith(b"\r\n\r\n")


async def test_streamed_request_body_is_sent_chunked(transport):
    async def body():
        yield b"abc"
        yield b"def"

    async with RawServer() as server:
        await send(transport, httpx.Request("POST", server.url, headers=[("host", "stub")], content=body()))
    head, _, sent = server.requests[0].partition(b"\r\n\r\n")
    assert b"Transfer-Encoding: chunked" in head
    assert sent.replace(b"\r\n", b"") == b"abcdef"


# --- what comes back -------------------------------------------------------------------------------------------------


async def test_status_reason_and_body(transport):
    reply = b"HTTP/1.1 418 I'm a teapot\r\nContent-Length: 4\r\n\r\ntea!"
    async with RawServer(reply) as server:
        response, raw = await send(transport, get(server.url))
    assert (response.status_code, response.reason_phrase, raw) == (418, "I'm a teapot", b"tea!")


async def test_response_headers_keep_order_duplicates_and_casing(transport):
    reply = b"HTTP/1.1 200 OK\r\nX-B: 1\r\nSet-Cookie: a=1\r\nx-a: 2\r\nSet-Cookie: b=2\r\nContent-Length: 0\r\n\r\n"
    async with RawServer(reply) as server:
        response, _ = await send(transport, get(server.url))
    assert response.headers.raw == [
        (b"X-B", b"1"),
        (b"Set-Cookie", b"a=1"),
        (b"x-a", b"2"),
        (b"Set-Cookie", b"b=2"),
        (b"Content-Length", b"0"),
    ]


async def test_body_is_delivered_undecoded(transport):
    body = gzip.compress(b"hello hello hello")
    reply = b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: %d\r\n\r\n" % len(body) + body
    async with RawServer(reply) as server:
        response, raw = await send(transport, get(server.url))
    assert response.headers["content-encoding"] == "gzip"
    assert raw == body


async def test_content_is_decoded_by_httpx_on_read(transport):
    body = gzip.compress(b"hello hello hello")
    reply = b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: %d\r\n\r\n" % len(body) + body
    async with RawServer(reply) as server:
        response = await transport.handle_async_request(get(server.url))
        await response.aread()
    assert response.content == b"hello hello hello"


async def test_chunked_response_body(transport):
    reply = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n4\r\ndefg\r\n0\r\n\r\n"
    async with RawServer(reply) as server:
        response, raw = await send(transport, get(server.url))
    assert raw == b"abcdefg"
    assert response.headers["transfer-encoding"] == "chunked"


async def test_response_without_length_ends_with_the_connection(transport):
    async with RawServer(b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\nuntil the end", close=True) as server:
        _, raw = await send(transport, get(server.url))
    assert raw == b"until the end"


async def test_head_response_has_no_body(transport):
    async with RawServer(b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n") as server:
        response, raw = await send(transport, httpx.Request("HEAD", server.url))
    assert (response.headers["content-length"], raw) == ("10", b"")


async def test_redirects_are_not_followed(transport):
    reply = b"HTTP/1.1 302 Found\r\nLocation: /elsewhere\r\nContent-Length: 0\r\n\r\n"
    async with RawServer(reply) as server:
        response, _ = await send(transport, get(server.url))
    assert (response.status_code, response.headers["location"]) == (302, "/elsewhere")
    assert len(server.requests) == 1


# --- pool and keep-alive ---------------------------------------------------------------------------------------------


async def test_connections_are_kept_alive(transport):
    async with RawServer() as server:
        for _ in range(3):
            await send(transport, get(server.url))
    assert (len(server.requests), server.connections) == (3, 1)


async def test_connections_are_bounded_by_the_pool_limit(make_transport):
    transport = make_transport(limits=httpx.Limits(max_connections=2))
    async with RawServer(delay=0.1) as server:
        await asyncio.gather(*(send(transport, get(server.url)) for _ in range(6)))
    assert (len(server.requests), server.max_in_flight) == (6, 2)


async def test_waiting_for_the_pool_is_a_timeout(make_transport):
    transport = make_transport(limits=httpx.Limits(max_connections=1))
    timeout = {"connect": 5, "read": 5, "write": 5, "pool": 0.2}
    async with RawServer(delay=1) as server:
        slow = asyncio.ensure_future(send(transport, get(server.url, extensions={"timeout": timeout})))
        await asyncio.sleep(0.1)
        with pytest.raises(httpx.TimeoutException):
            await send(transport, get(server.url, extensions={"timeout": timeout}))
        await slow


# --- timeouts and errors, as the exceptions the proxy answers for ----------------------------------------------------


async def test_read_timeout(transport):
    async with RawServer(delay=1) as server:
        request = get(server.url, extensions={"timeout": {"read": 0.1, "connect": 1, "write": 1, "pool": 1}})
        with pytest.raises(httpx.ReadTimeout):
            await send(transport, request)


async def test_connect_timeout(transport):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(0)  # never accepts: once the queue is full, connections hang
    fillers = []
    try:
        for _ in range(3):
            filler = socket.socket()
            filler.setblocking(False)
            filler.connect_ex(listener.getsockname())
            fillers.append(filler)
        request = get(
            f"http://127.0.0.1:{listener.getsockname()[1]}",
            extensions={"timeout": {"connect": 0.2, "read": 1, "write": 1, "pool": 1}},
        )
        with pytest.raises(httpx.ConnectTimeout):
            await send(transport, request)
    finally:
        for filler in fillers:
            filler.close()
        listener.close()


async def test_connection_refused_is_a_connect_error(transport):
    with pytest.raises(httpx.ConnectError):
        await send(transport, get("http://127.0.0.1:1"))


async def test_connection_reset_is_a_network_error(transport):
    async with RawServer(reset=True) as server:
        with pytest.raises(httpx.NetworkError):
            await send(transport, get(server.url))


async def test_server_closing_without_answer_is_a_remote_protocol_error(transport):
    async with RawServer(b"") as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, get(server.url))


async def test_garbage_answer_is_a_remote_protocol_error(transport):
    async with RawServer(b"not http at all\r\n\r\n") as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, get(server.url))


async def test_body_cut_short_is_a_remote_protocol_error(transport):
    async with RawServer(b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nabc", close=True) as server:
        with pytest.raises(httpx.RemoteProtocolError):
            await send(transport, get(server.url))


# --- TLS -------------------------------------------------------------------------------------------------------------


@pytest.fixture
def tls(tmp_path):
    key, certificate = tmp_path / "key.pem", tmp_path / "cert.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=127.0.0.1"]
        + ["-addext", "subjectAltName=IP:127.0.0.1", "-keyout", str(key), "-out", str(certificate)],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    return context


async def test_certificate_is_verified_by_default(transport, tls):
    async with RawServer(ssl_context=tls) as server:
        with pytest.raises(httpx.ConnectError):
            await send(transport, get(server.url))


async def test_verification_can_be_turned_off(make_transport, tls):
    transport = make_transport(verify=False)
    async with RawServer(ssl_context=tls) as server:
        response, raw = await send(transport, get(server.url))
    assert (response.status_code, raw) == (200, b"ok")


# --- arguments: honoured or refused, never ignored -------------------------------------------------------------------


def test_unknown_argument_is_refused(transport_type):
    with pytest.raises(TypeError):
        transport_class(transport_type)(no_such_argument=1)


def test_retries_are_accepted_at_zero(transport_type):
    transport_class(transport_type)(retries=0)


@pytest.mark.parametrize("transport_type", [AIOHTTP])
def test_aiohttp_refuses_what_it_cannot_honour(transport_type):
    cls = transport_class(transport_type)
    with pytest.raises(ValueError, match="retries"):
        cls(retries=1)
    with pytest.raises(ValueError, match="max_keepalive_connections"):
        cls(limits=httpx.Limits(max_keepalive_connections=20))
    with pytest.raises(ValueError, match="verify"):
        cls(verify="/path/to/ca.pem")
