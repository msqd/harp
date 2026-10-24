"""A failing cache storage neither breaks the response nor charges the upstream (#1272)."""

import httpx
import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy

from harp.http import HttpRequest
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_TRANSACTION_ENDED
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://example.com/"
BODY = b"0123456789" * 100


class FailingBlobStorage(MemoryBlobStorage):
    def __init__(self, failing: str):
        super().__init__()
        self.failing = failing

    async def put(self, *args, **kwargs):
        if self.failing == "put":
            raise ConnectionError("blob storage down")
        return await super().put(*args, **kwargs)

    async def get(self, *args, **kwargs):
        if self.failing == "get":
            raise ConnectionError("blob storage down")
        return await super().get(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        if self.failing == "delete":
            raise ConnectionError("blob storage down")
        return await super().delete(*args, **kwargs)


class EndedTransactions:
    def __init__(self):
        self.transactions = []

    async def adispatch(self, event_id, event=None):
        if event_id == EVENT_TRANSACTION_ENDED:
            self.transactions.append(event.transaction)
        return event


@pytest.mark.parametrize("operation", ["put", "get", "delete"])
@respx.mock
async def test_failing_cache_storage_leaves_response_transaction_and_endpoint_intact(operation):
    respx.get(URL).mock(return_value=httpx.Response(200, content=BODY, headers={"cache-control": "max-age=3600"}))
    respx.post(URL).mock(return_value=httpx.Response(200, content=BODY))
    remote = Remote.from_settings_dict({"liveness": {"type": "naive"}, "endpoints": [{"url": URL}]})
    dispatcher = EndedTransactions()
    controller = HttpProxyController(
        remote,
        http_client=httpx.AsyncClient(
            transport=AsyncCacheTransport(
                next_transport=httpx.AsyncHTTPTransport(),
                storage=AsyncStorage(FailingBlobStorage(operation)),
                policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
            )
        ),
        name="api",
        dispatcher=dispatcher,
    )

    for method in ("GET", "GET", "POST"):
        response = await controller(HttpRequest(method=method, path="/"))
        assert await response.aread() == BODY

    assert [t.extras["status_class"] for t in dispatcher.transactions] == ["2xx", "2xx", "2xx"]
    assert remote[URL].status > 0
    assert remote.current_pool
