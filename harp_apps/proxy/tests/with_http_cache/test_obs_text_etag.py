"""An ETag holding obs-text (bytes above 0x7F, RFC 9110 §5.5) is a valid field value, not a crash.

Field values are opaque octets, so they travel as latin-1 text: one char per byte, in both
directions, through the client and through the cache.
"""

import respx
from httpx import Response

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint
from harp_apps.proxy.tests.with_http_cache.test_hop_by_hop_responses import CLIENTS, _proxy

OBS_ETAG = b'"\xe9t\xff"'


@CLIENTS
async def test_obs_text_etag_is_proxied_byte_for_byte(make_client):
    response = Response(200, content=b"hello", headers=[(b"cache-control", b"max-age=3600"), (b"etag", OBS_ETAG)])
    headers = await _proxy(make_client, response, times=2)
    assert headers["etag"] == OBS_ETAG.decode("latin-1")


@CLIENTS
async def test_obs_text_if_none_match_is_sent_upstream_byte_for_byte(make_client):
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com/"})
    controller = HttpProxyController(http_client=make_client(), remote=endpoint.remote, name=endpoint.settings.name)
    request = HttpRequest(method="GET", path="/", headers={"if-none-match": OBS_ETAG.decode("latin-1")})
    with respx.mock:
        route = respx.get("http://example.com/").mock(return_value=Response(304))
        result = await controller(request)
    assert (b"if-none-match", OBS_ETAG) in route.calls.last.request.headers.raw
    assert result.status == 304
