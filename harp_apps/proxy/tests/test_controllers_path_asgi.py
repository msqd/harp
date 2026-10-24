"""End to end: a percent-encoded path as an ASGI server delivers it (``raw_path`` keeps the encoding, ``path``
is decoded) reaches the proxy controller, and either gets a 400 with the upstream untouched, or is forwarded
byte for byte."""

from unittest.mock import AsyncMock
from urllib.parse import unquote

import pytest
from httpx import AsyncByteStream, AsyncClient, MockTransport, Response

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.http import HttpRequest
from harp_apps.proxy.constants import UP
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint

BASE_URL = "http://upstream/api/v1/"

REFUSED_SEGMENTS = [
    "%2e%2e",
    "%2E%2E",
    ".%2e",
    "%2e.",
    "..%2f",
    "%2e%2e%2f",
    "..%5c",
    "..\\",
    "%252e%252e",
    "..%252f",
    "%25%32%65%25%32%65",
    "%25252e%25252e",
    "..;",
    "%2e%2e;jsessionid=x",
    "..%00",
    "%c0%ae%c0%ae",
    "%ef%bc%8e%ef%bc%8e",
    ".%2E/%2e.",
]

REFUSED_PATHS = [
    path
    for segment in REFUSED_SEGMENTS
    for path in (
        f"/{segment}/admin",
        f"/x/{segment}/{segment}/admin",
        f"/x/{segment}",
    )
]

FORWARDED_PATHS = ["/.well-known/x", "/v1.2/x", "/a%2eb", "/a%20b", "/a%2fb"]


class _EmptyStream(AsyncByteStream):
    async def __aiter__(self):
        yield b""


def _asgi_request(raw_path: str) -> HttpRequest:
    """The request as an ASGI server hands it over: ``raw_path`` as on the wire, ``path`` decoded."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": unquote(raw_path),
        "raw_path": raw_path.encode(),
        "query_string": b"",
        "headers": [],
        "server": ["127.0.0.1", 80],
    }
    receive = AsyncMock(return_value={"type": "http.request", "body": b"", "more_body": False})
    return HttpRequest(HttpRequestAsgiBridge(scope, receive))


@pytest.fixture
def sent():
    return []


@pytest.fixture
def endpoint():
    # A naive liveness with a threshold of one: a single counted failure would take the remote down.
    endpoint = Endpoint.from_kwargs(
        settings={
            "name": "test",
            "port": 80,
            "remote": {"endpoints": [{"url": BASE_URL, "liveness": {"type": "naive", "failure_threshold": 1}}]},
        }
    )
    endpoint.remote.set_up(BASE_URL)
    return endpoint


@pytest.fixture
def controller(endpoint, sent):
    def upstream(request):
        sent.append(request.url.raw_path.decode("ascii"))
        return Response(200, stream=_EmptyStream())

    client = AsyncClient(transport=MockTransport(upstream))
    return HttpProxyController(http_client=client, remote=endpoint.remote, name="test", logging=False)


@pytest.mark.parametrize("raw_path", REFUSED_PATHS)
async def test_hostile_dot_segment_answers_400_and_never_reaches_the_upstream(controller, sent, raw_path):
    response = await controller(_asgi_request(raw_path))
    assert response.status == 400
    assert sent == []


@pytest.mark.parametrize("raw_path", FORWARDED_PATHS)
async def test_legitimate_path_is_forwarded_byte_for_byte(controller, sent, raw_path):
    response = await controller(_asgi_request(raw_path))
    assert response.status == 200
    assert sent == ["/api/v1" + raw_path]


async def test_refused_requests_do_not_count_against_the_remote(controller, endpoint, sent):
    for raw_path in REFUSED_PATHS:
        await controller(_asgi_request(raw_path))
    assert sent == []
    assert endpoint.remote[BASE_URL].status == UP
    assert not endpoint.remote[BASE_URL].failure_reasons
