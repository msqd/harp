"""The proxy hands its transaction's redaction and markers to the http cache (ADR-0009)."""

import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.http import HttpRequest
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST
from harp_apps.proxy.settings.remote import Remote
from harp_apps.http_cache.records import MemoryCacheRecords


class Rule:
    """A dispatcher running ``edit`` on the transaction, as an ``on_request`` rule would."""

    def __init__(self, edit):
        self.edit = edit

    async def adispatch(self, event_id, event=None):
        if event_id == EVENT_FILTER_PROXY_REQUEST:
            self.edit(event.transaction)
        return event


async def _upstream_calls(edit, path="/") -> int:
    route = respx.get("http://example.com/").mock(
        return_value=Response(200, content=b"ok", headers={"cache-control": "max-age=3600"})
    )
    client = AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryCacheRecords()),
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )
    )
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": "http://example.com/"}]}),
        http_client=client,
        name="api",
        dispatcher=Rule(edit),
    )
    for _ in range(2):
        response = await controller(HttpRequest(method="GET", path=path, query={"client_secret": "x"}))
        await response.aread()
    return route.call_count


@respx.mock
async def test_a_query_parameter_redacted_by_a_rule_does_not_keep_the_response_out_of_the_cache():
    """The cache key holds a hash of the query, and the url is stored redacted: nothing to withhold."""
    assert await _upstream_calls(lambda transaction: transaction.redaction.query.add("client_secret")) == 1


@respx.mock
async def test_a_skip_marker_set_by_a_rule_keeps_the_response_out_of_the_cache():
    assert await _upstream_calls(lambda transaction: transaction.markers.add("skip-response-storage")) == 2


@respx.mock
async def test_without_a_rule_the_response_is_cached():
    assert await _upstream_calls(lambda transaction: None) == 1
