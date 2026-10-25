"""HARP's own credentials never reach an origin (ADR-0010)."""

import httpx
import respx

from harp.http import HttpRequest
from harp.security.credentials import generate_token
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.constants import HARP_CREDENTIALS_STRIPPED

BASE_URL = "http://example.com"


class RecordingDispatcher:
    def __init__(self):
        self.transaction = None
        self.recorded_headers = None

    async def adispatch(self, event_id, event=None):
        if event_id == EVENT_TRANSACTION_STARTED:
            self.transaction = event.transaction
        if event_id == EVENT_TRANSACTION_MESSAGE and event.message.kind == "request":
            self.recorded_headers = [(k.lower(), v) for k, v in event.message.headers.items()]
        return event


async def proxy(headers):
    dispatcher = RecordingDispatcher()
    remote = Remote.from_settings_dict({"endpoints": [{"url": BASE_URL}]})
    controller = HttpProxyController(remote, http_client=httpx.AsyncClient(), dispatcher=dispatcher, name="api")
    response = await controller(HttpRequest(headers=headers))
    b"".join([chunk async for chunk in response.stream])
    return dispatcher


@respx.mock
async def test_session_cookies_and_harp_bearer_do_not_reach_the_origin():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200))

    dispatcher = await proxy(
        {
            "cookie": "theme=dark; __Host-harp_session=secret; harp_session=secret; lang=fr",
            "authorization": f"Bearer {generate_token()}",
        }
    )

    (call,) = route.calls
    assert call.request.headers["cookie"] == "theme=dark; lang=fr"
    assert "authorization" not in call.request.headers
    assert HARP_CREDENTIALS_STRIPPED in dispatcher.transaction.markers
    # the recorded request message loses them too
    assert dispatcher.recorded_headers == [("cookie", "theme=dark; lang=fr")]


@respx.mock
async def test_emptied_cookie_header_is_not_forwarded():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200))

    await proxy({"cookie": "harp_session=secret"})

    assert "cookie" not in route.calls.last.request.headers


@respx.mock
async def test_other_credentials_are_forwarded_unchanged_and_unmarked():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200))

    dispatcher = await proxy({"cookie": "a=1", "authorization": "Bearer not-a-harp-token"})

    request = route.calls.last.request
    assert request.headers["cookie"] == "a=1"
    assert request.headers["authorization"] == "Bearer not-a-harp-token"
    assert HARP_CREDENTIALS_STRIPPED not in dispatcher.transaction.markers
