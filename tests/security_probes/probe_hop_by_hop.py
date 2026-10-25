"""Probe 4: connection-specific headers stop at the proxy, in both directions.

Fixes: ``373ffa89`` (#886, request path) and ``7379745f`` (#930, response path). Negative controls: ``87dfced3``
forwards ``te``, ``trailer``, ``upgrade``, ``proxy-authorization`` and the header named by ``Connection``; ``0.10.0``
returns all five response hop-by-hop headers and the header named by the origin's ``Connection``.

Forwarding headers (#1425) are part of the request path reading: a spoofed ``X-Forwarded-For`` from an untrusted peer
must not reach the origin.
"""

from tests.security_probes.raw import Response, send_raw

REQUEST_HOP_BY_HOP = ["keep-alive", "te", "trailer", "upgrade", "proxy-authorization"]
RESPONSE_HOP_BY_HOP = ["keep-alive", "trailer", "upgrade", "proxy-authenticate"]


def test_4a_hop_by_hop_request_headers_do_not_reach_the_origin(flat, origin):
    raw = (
        b"GET /hop HTTP/1.1\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Connection: keep-alive, X-Client-Secret\r\n"
        b"X-Client-Secret: should-be-dropped\r\n"
        b"Keep-Alive: timeout=5\r\n"
        b"TE: trailers\r\n"
        b"Trailer: X-Client-Trailer\r\n"
        b"Upgrade: websocket\r\n"
        b"Proxy-Authorization: Basic Y2xpZW50OnNlY3JldA==\r\n"
        b"X-Forwarded-For: 6.6.6.6\r\n"
        b"X-Client-Plain: kept\r\n"
        b"\r\n"
    )

    response = Response(send_raw(flat, raw))

    assert response.status == 200
    assert len(origin.requests) == 1
    forwarded = origin.requests[0]
    assert forwarded["header_names"].count("x-client-plain") == 1, "an ordinary header must survive"
    leaked = [name for name in REQUEST_HOP_BY_HOP if name in forwarded["header_names"]]
    assert not leaked, f"hop-by-hop request headers reached the origin: {leaked}"
    assert "x-client-secret" not in forwarded["header_names"], "the header named by Connection reached the origin"
    assert "6.6.6.6" not in forwarded["raw_head"], (
        "a spoofed forwarding header from an untrusted peer reached the origin"
    )


def test_4b_hop_by_hop_response_headers_do_not_reach_the_client(flat, origin):
    response = Response(send_raw(flat, b"GET /hopresp HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"))

    assert response.status == 200
    assert "x-origin-plain" in response.names, "an ordinary header must survive"
    leaked = [name for name in RESPONSE_HOP_BY_HOP if name in response.names]
    assert not leaked, f"hop-by-hop response headers reached the client: {leaked}"
    assert "x-origin-secret" not in response.names, "the header named by the origin's Connection reached the client"
    assert "origin" not in (response.header("connection") or ""), "the origin's Connection value was relayed"
