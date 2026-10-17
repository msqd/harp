"""Header values are opaque octets (RFC 9110 §5.5): obs-text must cross the ASGI bridge unchanged."""

from unittest.mock import AsyncMock

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.asgi.bridge.responses import HttpResponseAsgiBridge
from harp.http import HttpResponse

OBS_ETAG = b'"abcdef\xfc"'


def test_request_header_with_obs_text_is_decoded():
    bridge = HttpRequestAsgiBridge({"headers": [(b"if-none-match", OBS_ETAG)]}, AsyncMock())
    assert bridge.get_headers()["if-none-match"] == OBS_ETAG.decode("latin-1")


async def test_response_header_with_obs_text_is_sent_unchanged():
    send = AsyncMock()
    response = HttpResponse(b"", headers={"etag": OBS_ETAG.decode("latin-1")})
    await HttpResponseAsgiBridge(response, send).send()
    assert (b"etag", OBS_ETAG) in send.call_args_list[0].args[0]["headers"]
