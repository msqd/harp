"""Probes 1 and 2: the request path cannot make the proxy reach somewhere its endpoint does not expose.

Fix: ``233bd99a`` (#855), since reworked: the forwarded URL is the endpoint's origin and base path followed by the raw
path. Negative control: ``48261dce``, where ``GET /http://example.org/`` is answered 200 with the real example.org body
(the configured origin sees nothing) and ``GET /../../admin`` makes the origin see ``GET /admin``.

Probe 2's refusal is paired with a control request that is forwarded and answered 200, so a 400 cannot be a dead
endpoint. Probe 1 needs no refusal: its pass condition is that the configured origin, and only it, got the request.
"""

from tests.security_probes.raw import RawOrigin, Response, send_raw


def get(port: int, target: str) -> Response:
    return Response(send_raw(port, f"GET {target} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode()))


def test_control_ordinary_request_is_forwarded(flat, origin):
    assert get(flat, "/ordinary").status == 200
    assert [r["request_line"] for r in origin.requests] == ["GET /ordinary HTTP/1.1"]


def test_1_scheme_in_path_stays_a_path_on_the_configured_upstream(flat, origin):
    """On ``main`` the forwarded URL is the endpoint's origin followed by the raw path, so a scheme in the path is not
    refused any more: it can only ever land on the configured upstream, as a path. The vulnerable build sent the
    request to example.org (the origin saw nothing)."""
    assert get(flat, "/ordinary").status == 200
    origin.requests.clear()

    response = get(flat, "/http://example.org/")

    assert response.status == 200
    assert RawOrigin.PAYLOAD in response.body, "SSRF (CWE-918): the answer did not come from the configured origin"
    assert [r["request_line"] for r in origin.requests] == ["GET /http://example.org/ HTTP/1.1"], (
        "SSRF (CWE-918): the request did not reach the configured origin as a path"
    )


def test_1_authority_in_path_is_dropped_not_followed(flat, origin):
    assert get(flat, "/ordinary").status == 200
    origin.requests.clear()

    response = get(flat, "//example.org/")

    assert response.status == 200
    assert RawOrigin.PAYLOAD in response.body, "SSRF (CWE-918): the answer did not come from the configured origin"
    assert [r["request_line"] for r in origin.requests] == ["GET / HTTP/1.1"], (
        "SSRF (CWE-918): the authority in the path was followed"
    )


def test_control_subtree_endpoint_forwards_under_its_prefix(sub, origin):
    assert get(sub, "/thing").status == 200
    assert [r["request_line"] for r in origin.requests] == ["GET /api/v1/thing HTTP/1.1"]


def test_2_dot_segments_cannot_leave_the_exposed_subtree(sub, origin):
    control = get(sub, "/thing")
    assert control.status == 200
    origin.requests.clear()

    response = get(sub, "/../../admin")

    assert response.status == 400, "dot-segment escape: the proxy answered with " + response.status_line
    assert origin.requests == [], f"the origin saw {[r['request_line'] for r in origin.requests]}"
