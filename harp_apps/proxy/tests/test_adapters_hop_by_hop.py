"""What a proxy must not pass on when it forwards a request.

Two rules from the HTTP specification, both of which HARP sits squarely inside as an
intermediary:

- RFC 9110 §7.6.1: connection-specific header fields apply to a single connection and must not be
  forwarded onto the next one.
- RFC 9112 §6.1: a message carrying both ``Content-Length`` and ``Transfer-Encoding`` is malformed
  and an intermediary must not forward it. Recipients disagree about which of the two wins, and
  forwarding the disagreement is what turns it into a desynchronised connection.

The framing headers are the client's claim about a body HARP has already read and is re-sending
itself, so httpx is left to state the framing of what it actually sends.
"""

import asyncio

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp_apps.proxy.adapters import HttpClientProxyAdapter


async def _forward(headers, body=b"hello world"):
    """Forward a request through the adapter and return the raw bytes the upstream received."""
    received = asyncio.Queue()

    async def upstream(reader, writer):
        # Give the client time to write the whole request before reading it in one go.
        await asyncio.sleep(0.2)
        await received.put(await reader.read(65536))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(upstream, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        async with AsyncClient() as client:
            adapter = HttpClientProxyAdapter(client, extensions={"endpoint": "test"})
            request = HttpRequest(method="POST", path="/x", headers=headers, body=body)
            await request.aread()
            await adapter.send(request, f"http://127.0.0.1:{port}/x")
        return (await received.get()).decode("latin-1")
    finally:
        server.close()


def _header_lines(wire: str) -> list[str]:
    head = wire.split("\r\n\r\n", 1)[0]
    return [line.lower() for line in head.split("\r\n")[1:]]


@pytest.mark.asyncio
async def test_conflicting_framing_headers_are_not_forwarded():
    """A client claiming both a length and a chunked encoding must not reach the upstream.

    The body really is 11 bytes. An upstream honouring the client's ``content-length: 3`` would
    leave the remaining bytes in the connection buffer, where they become the start of whatever
    request is sent next over that pooled connection.
    """
    wire = await _forward({"content-length": "3", "transfer-encoding": "chunked"})
    lines = _header_lines(wire)

    assert not any(line.startswith("transfer-encoding:") for line in lines), wire
    assert "content-length: 3" not in lines, wire
    assert "content-length: 11" in lines, wire
    assert wire.endswith("hello world"), wire


@pytest.mark.asyncio
async def test_the_client_declared_length_never_overrides_the_real_one():
    """HARP re-sends a body it has already read, so it states that body's length, not a claim."""
    wire = await _forward({"content-length": "999"})

    assert "content-length: 11" in _header_lines(wire), wire


@pytest.mark.parametrize(
    "header",
    [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    ],
)
@pytest.mark.asyncio
async def test_connection_specific_headers_are_not_forwarded(header):
    wire = await _forward({header: "whatever", "x-kept": "yes"})
    lines = _header_lines(wire)

    assert not any(line.startswith(f"{header}: whatever") for line in lines), wire
    assert "x-kept: yes" in lines, wire


@pytest.mark.asyncio
async def test_headers_named_by_connection_are_not_forwarded():
    """``Connection`` names further headers that are also single-connection only."""
    wire = await _forward({"connection": "keep-alive, X-Hop, X-Other", "x-hop": "no", "x-other": "no", "x-kept": "yes"})
    lines = _header_lines(wire)

    assert "x-hop: no" not in lines, wire
    assert "x-other: no" not in lines, wire
    assert "x-kept: yes" in lines, wire


@pytest.mark.asyncio
async def test_ordinary_headers_still_reach_the_upstream():
    wire = await _forward({"authorization": "Bearer t0ken", "accept": "application/json"})
    lines = _header_lines(wire)

    assert "authorization: Bearer t0ken".lower() in lines, wire
    assert "accept: application/json" in lines, wire
