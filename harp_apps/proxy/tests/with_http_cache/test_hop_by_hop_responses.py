"""What a proxy must not pass back when it returns a response, in both configurations.

The mirror of ``test_adapters_hop_by_hop.py``, which covers the request direction. RFC 9110 §7.6.1
binds an intermediary in both directions: a field describing the connection a message arrived on
must not travel onto the next connection, whichever way the message is going.

**Every test here runs twice, once without the cache and once with it, and that is the point.**
hishel removes ``Connection`` from the response during its own processing and leaves the fields it
named behind. So with the cache in the path the controller is handed orphaned fields and nothing to
identify them by, and a version of this suite that only built a plain client would pass while the
shipped configuration, in which ``http_cache`` is a default application, still leaked them.
"""

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.http import HttpRequest
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import Endpoint
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage


def _uncached_client():
    return AsyncClient()


def _cached_client():
    return AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryBlobStorage()),
            policy=SpecificationPolicy(
                cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
            ),
        )
    )


CLIENTS = pytest.mark.parametrize("make_client", [_uncached_client, _cached_client], ids=["no-cache", "with-cache"])


async def _proxy(make_client, response: Response, times: int = 1) -> dict:
    """Proxy `times` upstream responses and return the headers the client ends up with."""
    endpoint = Endpoint.from_kwargs(settings={"name": "test", "port": 80, "url": "http://example.com/"})
    controller = HttpProxyController(
        http_client=make_client(), remote=endpoint.remote, name=endpoint.settings.name
    )
    with respx.mock:
        respx.get("http://example.com/").mock(return_value=response)
        for _ in range(times):
            result = await controller(HttpRequest(method="GET", path="/"))
    return {name.lower(): value for name, value in result.headers.items()}


def _cacheable(**headers):
    return Response(200, content=b"hello", headers={"cache-control": "max-age=3600", **headers})


@CLIENTS
@pytest.mark.parametrize("name", ["connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-authenticate"])
async def test_connection_specific_response_headers_are_dropped(make_client, name):
    # These describe the upstream connection, not the response, so they stop at the hop.
    assert name not in await _proxy(make_client, _cacheable(**{name: "whatever"}))


@CLIENTS
async def test_fields_named_by_connection_are_dropped(make_client):
    # The point of `Connection` is that it names *other* fields as connection-specific. Dropping
    # `Connection` itself and passing on what it named is the half-fix that looks correct.
    headers = await _proxy(make_client, _cacheable(connection="a, b", a="1", b="2", c="3"))
    assert "a" not in headers
    assert "b" not in headers
    assert headers["c"] == "3"


@CLIENTS
async def test_named_fields_are_dropped_from_a_cached_response_too(make_client):
    # Second request, served from cache when there is one. A response replayed from storage must
    # not carry what the first one was not allowed to carry.
    headers = await _proxy(make_client, _cacheable(connection="a, b", a="1", b="2", c="3"), times=2)
    assert "a" not in headers
    assert "b" not in headers
    assert headers["c"] == "3"


@CLIENTS
async def test_connection_field_names_are_matched_case_insensitively(make_client):
    assert "x-custom" not in await _proxy(make_client, _cacheable(connection="X-Custom", **{"x-custom": "1"}))


@CLIENTS
async def test_ordinary_response_headers_still_reach_the_client(make_client):
    headers = await _proxy(make_client, _cacheable(**{"content-type": "text/plain", "x-app": "yes", "etag": '"v1"'}))
    assert headers["content-type"] == "text/plain"
    assert headers["x-app"] == "yes"
    assert headers["etag"] == '"v1"'


@CLIENTS
async def test_a_connection_token_that_names_nothing_is_harmless(make_client):
    # `close` and `keep-alive` are connection options rather than field names. Nothing else should
    # disappear because one of them was present.
    headers = await _proxy(make_client, _cacheable(connection="close", **{"x-app": "yes"}))
    assert headers["x-app"] == "yes"
    assert "connection" not in headers
