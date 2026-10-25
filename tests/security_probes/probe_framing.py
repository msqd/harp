"""Probe 3: a request that states its body length twice is refused, not forwarded with a framing HARP picked.

Fix: ``373ffa89`` (#886), then #1426: ``Content-Length`` together with ``Transfer-Encoding`` is answered 400 with
``Connection: close`` and never reaches the origin. Negative control: ``87dfced3``, which forwards the request
declaring ``Content-Length: 5`` and sending 0 bytes.

The refusal is paired with a control: the same request with a single, unambiguous framing is forwarded whole.
"""

from tests.security_probes.raw import Response, send_raw


def post(port: int, *framing: bytes, body: bytes) -> Response:
    head = b"POST /smuggle HTTP/1.1\r\nHost: 127.0.0.1\r\n" + b"".join(line + b"\r\n" for line in framing) + b"\r\n"
    return Response(send_raw(port, head + body))


def test_control_a_single_framing_is_forwarded_whole(flat, origin):
    response = post(flat, b"Content-Length: 5", body=b"hello")

    assert response.status == 200
    assert [r["body"] for r in origin.requests] == [b"hello"]


def test_3_content_length_with_transfer_encoding_is_refused(flat, origin):
    control = post(flat, b"Content-Length: 5", body=b"hello")
    assert control.status == 200
    origin.requests.clear()

    response = post(flat, b"Content-Length: 5", b"Transfer-Encoding: chunked", body=b"0\r\n\r\n")

    assert response.status == 400, "request smuggling: CL+TE was answered " + response.status_line
    assert (response.header("connection") or "").lower() == "close"
    assert origin.requests == [], f"the origin was reached: {origin.requests}"
