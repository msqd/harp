"""A request body above ``max_request_body_size`` is answered 413, and the upstream is never called (#1457)."""

import httpx
import respx
from httpx import AsyncByteStream

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import EndpointSettings, ProxySettings
from harp_apps.proxy.settings.remote import Remote

BASE_URL = "http://example.com"
CAP = 10


class NoDispatcher:
    async def adispatch(self, event_id, event=None):
        return event


class SpyStream(AsyncByteStream):
    def __init__(self, *chunks):
        self.chunks = chunks
        self.read = []

    async def __aiter__(self):
        for chunk in self.chunks:
            self.read.append(chunk)
            yield chunk


def create_controller(**kwargs):
    remote = Remote.from_settings_dict({"endpoints": [{"url": BASE_URL}]})
    return HttpProxyController(remote, http_client=httpx.AsyncClient(), dispatcher=NoDispatcher(), name="api", **kwargs)


def post(stream, **headers):
    request = HttpRequest(method="POST", headers=headers)
    request.stream = stream
    return request


@respx.mock
async def test_declared_length_above_the_cap_is_413_before_the_body_is_read():
    route = respx.post(BASE_URL).mock(return_value=httpx.Response(200))
    stream = SpyStream(b"x")
    request = post(stream, **{"Content-Length": str(CAP + 1)})

    response = await create_controller(max_request_body_size=CAP)(request)

    assert response.status == 413
    assert stream.read == []
    assert not route.called


@respx.mock
async def test_chunked_body_crossing_the_cap_is_413_mid_stream():
    route = respx.post(BASE_URL).mock(return_value=httpx.Response(200))
    stream = SpyStream(b"x" * 6, b"y" * 6, b"never read")
    request = post(stream)  # no content-length: chunked

    response = await create_controller(max_request_body_size=CAP)(request)

    assert response.status == 413
    assert stream.read == [b"x" * 6, b"y" * 6]
    assert not route.called


@respx.mock
async def test_body_at_the_cap_is_forwarded():
    route = respx.post(BASE_URL).mock(return_value=httpx.Response(200))
    request = post(SpyStream(b"x" * CAP), **{"Content-Length": str(CAP)})

    response = await create_controller(max_request_body_size=CAP)(request)

    assert response.status == 200
    assert route.called


def test_proxy_setting_has_a_default_and_an_endpoint_overrides_it():
    assert ProxySettings().max_request_body_size == 100 * 1024 * 1024
    assert ProxySettings(max_request_body_size="1MiB").max_request_body_size == 1024 * 1024
    assert EndpointSettings(name="a", url="http://x", max_request_body_size="2KiB").max_request_body_size == 2048
    assert EndpointSettings(name="a", url="http://x").max_request_body_size is None
