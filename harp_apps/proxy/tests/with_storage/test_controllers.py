from typing import Optional, cast
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.config.asdict import asdict
from harp.http import HttpRequest, HttpResponse
from harp.utils.bytes import ensure_bytes
from harp.utils.testing.mixins import ControllerTestFixtureMixin
from harp.utils.testing.mixins.controllers import _create_request
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_TRANSACTION_STARTED
from harp_apps.proxy.settings import TagsSettings
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.constants import SKIP_STORAGE, TRUNCATED_REQUEST_BODY, TRUNCATED_RESPONSE_BODY
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage
from harp_apps.storage.types import IBlobStorage, IStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin
from harp_apps.storage.worker import StorageAsyncWorkerQueue


class DispatcherTestFixtureMixin:
    @pytest.fixture(scope="function")
    def dispatcher(self):
        return AsyncEventDispatcher()


class HttpProxyControllerTestFixtureMixin(ControllerTestFixtureMixin):
    ControllerType = HttpProxyController

    @pytest.fixture(autouse=True)
    def setup(self):
        # forces the user agent to be a known value, even if versions are incremented
        with patch("harp_apps.proxy.adapters.HttpClientProxyAdapter.user_agent", "test/1.0"):
            yield

    def mock_http_endpoint(self, url, /, *, status=200, content=""):
        """Make sure you decorate your tests function using this with respx.mock decorator, otherwise the real network
        will be called and you may have some headaches..."""
        return respx.get(url).mock(return_value=Response(status, content=ensure_bytes(content)))

    def create_controller(
        self,
        url=None,
        *args,
        dispatcher: Optional[IAsyncEventDispatcher] = None,
        http_client=None,
        **kwargs,
    ):
        return super().create_controller(
            Remote.from_settings_dict({"endpoints": [{"url": url or "http://example.com/"}]}),
            *args,
            dispatcher=dispatcher,
            http_client=http_client or AsyncClient(),
            **kwargs,
        )

    def create_worker(
        self,
        dispatcher: IAsyncEventDispatcher,
        engine: AsyncEngine,
        sql_storage: IStorage,
        blob_storage: IBlobStorage,
    ) -> StorageAsyncWorkerQueue:
        worker = StorageAsyncWorkerQueue(engine, sql_storage, blob_storage)
        worker.register_events(dispatcher)
        return worker


class TestHttpProxyController(HttpProxyControllerTestFixtureMixin, DispatcherTestFixtureMixin):
    @respx.mock
    async def test_basic_get(self, dispatcher: IAsyncEventDispatcher):
        endpoint = self.mock_http_endpoint("http://example.com/", content="Hello.")
        request, response = await self.call_controller(
            self.create_controller("http://example.com/", dispatcher=dispatcher)
        )

        # check output and side effects
        assert endpoint.called and endpoint.call_count == 1
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b"Hello."

    @respx.mock
    async def test_get_with_tags(self, dispatcher: IAsyncEventDispatcher):
        endpoint = self.mock_http_endpoint("http://example.com/", content="Hello.")

        # register a mock handler to inspect the actually created transaction
        transaction_started_handler = AsyncMock()
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, transaction_started_handler)

        # call our controller
        request, response = await self.call_controller(
            self.create_controller("http://example.com/", dispatcher=dispatcher),
            headers={
                "x-harp-foo": "bar",
                "accept": "application/json",
                "vary": "custom",
            },
        )

        # check that our remote endpoint was passed custom headers, but not internal ones
        assert endpoint.called and endpoint.call_count == 1
        assert "x-harp-foo" not in endpoint.calls[0].request.headers
        assert endpoint.calls[0].request.headers["accept"] == "application/json"
        assert endpoint.calls[0].request.headers["vary"] == "custom"

        # check that the transaction was tagged with the expected values
        assert transaction_started_handler.called and transaction_started_handler.call_count == 1
        assert transaction_started_handler.call_args.args[0].transaction.tags == {"foo": "bar"}

        # check we got a valid response
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b"Hello."

    @respx.mock
    async def test_get_with_too_many_tags_is_proxied_with_the_first_ones(self, dispatcher: IAsyncEventDispatcher):
        endpoint = self.mock_http_endpoint("http://example.com/", content="Hello.")
        transaction_started_handler = AsyncMock()
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, transaction_started_handler)

        _, response = await self.call_controller(
            self.create_controller("http://example.com/", dispatcher=dispatcher),
            headers={f"x-harp-t{i}": "v" for i in range(200)} | {"x-harp-" + "n" * 65: "v"},
        )

        assert response.status == 200
        assert endpoint.call_count == 1
        tags = transaction_started_handler.call_args.args[0].transaction.tags
        assert list(tags) == [f"t{i}" for i in range(20)]

    @respx.mock
    async def test_tag_bounds_come_from_the_controller_settings(self, dispatcher: IAsyncEventDispatcher):
        self.mock_http_endpoint("http://example.com/", content="Hello.")
        transaction_started_handler = AsyncMock()
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, transaction_started_handler)

        await self.call_controller(
            self.create_controller("http://example.com/", dispatcher=dispatcher, tags=TagsSettings(max_count=1)),
            headers={"x-harp-a": "1", "x-harp-b": "2"},
        )

        assert transaction_started_handler.call_args.args[0].transaction.tags == {"a": "1"}

    @respx.mock
    async def test_dropped_tags_are_logged_with_the_transaction_not_the_value(self, dispatcher: IAsyncEventDispatcher):
        self.mock_http_endpoint("http://example.com/", content="Hello.")
        controller = self.create_controller("http://example.com/", dispatcher=dispatcher)

        with patch.object(controller, "debug") as debug:
            await self.call_controller(controller, headers={"x-harp-big": "secret-value" * 100})

        dropped = [call for call in debug.call_args_list if "client tag dropped" in call.args[0]]
        assert len(dropped) == 1
        assert dropped[0].kwargs["transaction"].id
        assert "secret-value" not in str(dropped[0].args)

    async def test_get_next_url_for(self):
        controller = self.create_controller("http://example.com/base/")
        request = await _create_request(path="/foo/bar/")
        context = Mock()
        context.request = request
        base_url, full_url = await controller._get_next_url_for(context)
        assert base_url == "http://example.com/base/"
        assert full_url == "http://example.com/base/foo/bar/"


class TestHttpProxyControllerWithStorage(
    HttpProxyControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    DispatcherTestFixtureMixin,
):
    async def call_controller(
        self,
        controller=None,
        /,
        *,
        dispatcher=None,
        engine=None,
        sql_storage=None,
        blob_storage=None,
        body=None,
        method="GET",
        headers=None,
    ) -> tuple[HttpRequest, HttpResponse]:
        dispatcher: IAsyncEventDispatcher = cast(IAsyncEventDispatcher, dispatcher or AsyncEventDispatcher())
        controller = controller or self.create_controller(dispatcher=dispatcher)
        worker = self.create_worker(dispatcher, engine, sql_storage, blob_storage)
        try:
            return await super().call_controller(controller, body=body, method=method, headers=headers)
        finally:
            await worker.wait_until_empty()

    async def _find_one_transaction_with_messages_from_storage(self, storage):
        # get transaction, request and response
        transactions = await storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        transaction = transactions[0]
        return transaction, transaction.messages[0], transaction.messages[1]

    @respx.mock
    async def test_basic_get(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        self.mock_http_endpoint("http://example.com/", content="Hello.")

        # register the storage
        await self.call_controller(
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
        )

        transaction, request, response = await self._find_one_transaction_with_messages_from_storage(sql_storage)
        assert asdict(transaction) == {
            "id": ANY,
            "type": "http",
            "endpoint": None,
            "elapsed": ANY,
            "tpdex": ANY,
            "started_at": ANY,
            "finished_at": ANY,
            "messages": ANY,
            "tags": {},
            "markers": [],
            "extras": {
                "flags": [],
                "method": "GET",
                "status_class": "2xx",
                "cached": False,
                "no_cache": False,
            },
        }

        # request
        request_headers = await blob_storage.get(request.headers)
        assert request_headers.data == b""
        assert request_headers.content_type == "http/headers"
        assert (await blob_storage.get(request.body)).data == b""
        assert asdict(request) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "e16aaad8ef3406ba55f2c90748d15fcbb6cdd66a",
            "body": "af5570f5a1810b7af78caf4bc70a660f0df51e42",
            "created_at": ANY,
        }

        # response
        response_headers = await blob_storage.get(response.headers)
        assert response_headers.data == b""
        assert response_headers.content_type == "http/headers"
        assert (await blob_storage.get(response.body)).data == b"Hello."
        assert asdict(response) == {
            "id": 2,
            "transaction_id": ANY,
            "kind": "response",
            "summary": "HTTP/1.1 200 OK",
            "headers": "e16aaad8ef3406ba55f2c90748d15fcbb6cdd66a",
            "body": "ce9e973bfc3d9e7e5c8987ea1ee70bbc00896a98",
            "created_at": ANY,
        }

    @respx.mock
    async def test_get_with_tags(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        self.mock_http_endpoint("http://example.com/", content="Hello.")

        # call our controller
        await self.call_controller(
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
            headers={
                "x-harp-foo": "bar",
                "accept": "application/json",
                "vary": "custom",
            },
        )

        transaction, request, response = await self._find_one_transaction_with_messages_from_storage(sql_storage)

        assert asdict(transaction) == {
            "id": ANY,
            "type": "http",
            "endpoint": None,
            "elapsed": ANY,
            "tpdex": ANY,
            "started_at": ANY,
            "finished_at": ANY,
            "messages": ANY,
            "tags": {"foo": "bar"},
            "markers": [],
            "extras": {
                "flags": [],
                "method": "GET",
                "status_class": "2xx",
                "cached": False,
                "no_cache": False,
            },
        }

        request_headers = await blob_storage.get(request.headers)
        assert request_headers.data == (b"accept: application/json\nvary: custom")
        assert request_headers.content_type == "http/headers"
        assert (await blob_storage.get(request.body)).data == b""
        assert asdict(request) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "c7a6a4abca83566b122a9d7117af9ae9bb9a5b60",
            "body": "af5570f5a1810b7af78caf4bc70a660f0df51e42",
            "created_at": ANY,
        }

        response_headers = await blob_storage.get(response.headers)
        assert response_headers.data == b""
        assert response_headers.content_type == "http/headers"
        assert (await blob_storage.get(response.body)).data == b"Hello."
        assert asdict(response) == {
            "id": 2,
            "transaction_id": ANY,
            "kind": "response",
            "summary": "HTTP/1.1 200 OK",
            "headers": "e16aaad8ef3406ba55f2c90748d15fcbb6cdd66a",
            "body": "ce9e973bfc3d9e7e5c8987ea1ee70bbc00896a98",
            "created_at": ANY,
        }

    def create_cache_backed_client(self) -> AsyncClient:
        """A client wired through HARP's cache, the way the proxy is given one in production.

        These tests need the real cache rather than an origin claiming to be one: whether a response
        came from HARP's cache is exactly what is under test, so it must not be an input.

        The cache keeps its blobs in memory rather than in the storage under test. What is asserted
        here is how a cache hit is reported, not how blobs are persisted, and sharing the blob store
        with the transaction recorder would put an unrelated backend in the path of every assertion.
        """
        return AsyncClient(
            transport=AsyncCacheTransport(
                next_transport=AsyncHTTPTransport(),
                storage=AsyncStorage(MemoryBlobStorage()),
                policy=SpecificationPolicy(
                    cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
                ),
            )
        )

    async def _proxy_repeatedly(self, controller, dispatcher, sql_storage, blob_storage, *, times):
        """Send `times` requests through one controller, so a cache has the chance to be used."""
        worker = self.create_worker(dispatcher, sql_storage.engine, sql_storage, blob_storage)
        responses = []
        try:
            for _ in range(times):
                response = await controller(await _create_request())
                await response.aread()
                responses.append(response)
        finally:
            await worker.wait_until_empty()
        return responses

    async def _find_transactions_from_storage(self, storage):
        transactions = await storage.get_transaction_list(username="anonymous", with_messages=True)
        return sorted(transactions, key=lambda transaction: transaction.started_at)

    @respx.mock
    async def test_cache_status_comes_from_the_cache_not_from_a_response_header(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        # The origin says nothing about cache status, so only HARP's own cache can answer. The
        # second request is the hit, and the origin is contacted once.
        endpoint = respx.get("http://example.com/").mock(
            return_value=Response(200, content=b"Hello.", headers={"Cache-Control": "max-age=3600"})
        )
        controller = self.create_controller(
            "http://example.com/",
            dispatcher=dispatcher,
            name="api",
            http_client=self.create_cache_backed_client(),
        )

        await self._proxy_repeatedly(controller, dispatcher, sql_storage, blob_storage, times=2)

        assert endpoint.call_count == 1
        # MySQL keeps `started_at` to the second, so two requests of one test tie and their order is
        # not recoverable from storage: assert on the set of outcomes, not on their order.
        transactions = await self._find_transactions_from_storage(sql_storage)
        assert sorted(t.extras["cached"] for t in transactions) == [False, True]

    @respx.mock
    async def test_an_upstream_x_cache_header_is_not_mistaken_for_our_own(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        # An origin behind a CDN announces its own cache status under this name: CloudFront, Fastly
        # and Varnish all do. It is the upstream's hit, not ours, and here HARP has no cache at all.
        respx.get("http://example.com/").mock(
            return_value=Response(200, content=b"Hello.", headers={"X-Cache": "HIT", "Age": "42"})
        )
        controller = self.create_controller("http://example.com/", dispatcher=dispatcher, name="api")

        await self._proxy_repeatedly(controller, dispatcher, sql_storage, blob_storage, times=1)

        (transaction,) = await self._find_transactions_from_storage(sql_storage)
        assert transaction.extras["cached"] is False
        assert "cache_age" not in transaction.extras

    @respx.mock
    async def test_cache_age_is_measured_by_our_own_cache(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        # The origin claims a large age. Ours is the time since we stored it, which is moments.
        respx.get("http://example.com/").mock(
            return_value=Response(200, content=b"Hello.", headers={"Cache-Control": "max-age=3600", "Age": "9999"})
        )
        controller = self.create_controller(
            "http://example.com/",
            dispatcher=dispatcher,
            name="api",
            http_client=self.create_cache_backed_client(),
        )

        _miss, hit = await self._proxy_repeatedly(controller, dispatcher, sql_storage, blob_storage, times=2)

        # `cache_age` lives in the runtime extras only and is never persisted, so the age has to be
        # read where a client would read it.
        transactions = await self._find_transactions_from_storage(sql_storage)
        assert sorted(t.extras["cached"] for t in transactions) == [False, True]
        assert int(hit.headers["Age"]) < 60

    @respx.mock
    async def test_cache_debugging_headers_are_sent_to_the_client(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        # `X-Cache` and `Age` on the outgoing response are a documented feature in their own right,
        # and they are the only remaining reason the adapter writes those headers at all.
        respx.get("http://example.com/").mock(
            return_value=Response(200, content=b"Hello.", headers={"Cache-Control": "max-age=3600"})
        )
        controller = self.create_controller(
            "http://example.com/",
            dispatcher=dispatcher,
            name="api",
            http_client=self.create_cache_backed_client(),
        )

        miss, hit = await self._proxy_repeatedly(controller, dispatcher, sql_storage, blob_storage, times=2)

        assert miss.headers["X-Cache"] == "MISS"
        assert hit.headers["X-Cache"] == "HIT"
        assert "Age" in hit.headers

    @respx.mock
    async def test_a_no_store_request_suppresses_its_payload_recording(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        """A caller's `no-store` binds the cache and suppresses payload recording (ADR-0002, #927).

        The transaction and both message rows stay, with their summaries; no headers, no bodies.
        """
        endpoint = respx.get("http://example.com/").mock(
            return_value=Response(200, content=b"Hello.", headers={"Cache-Control": "max-age=3600"})
        )
        controller = self.create_controller(
            "http://example.com/",
            dispatcher=dispatcher,
            name="api",
            http_client=self.create_cache_backed_client(),
        )

        worker = self.create_worker(dispatcher, sql_storage.engine, sql_storage, blob_storage)
        try:
            responses = []
            for _ in range(2):
                response = await controller(await _create_request(headers={"cache-control": "no-store"}))
                await response.aread()
                responses.append(response)
        finally:
            await worker.wait_until_empty()

        # The cache honoured the directive: the origin answered both times, and both responses
        # are reported as misses rather than one of them being a hit.
        assert endpoint.call_count == 2
        assert [response.headers["X-Cache"] for response in responses] == ["MISS", "MISS"]

        # The record keeps that the calls happened, without their payload, and says why.
        transactions = await self._find_transactions_from_storage(sql_storage)
        assert len(transactions) == 2
        for transaction in transactions:
            assert transaction.extras["cached"] is False
            assert {"no-store-request", "no-store-response"} <= set(transaction.markers)
            request_message, response_message = transaction.messages
            for message in (request_message, response_message):
                assert message.summary
                assert message.headers is None
                assert message.body is None

    @respx.mock
    async def test_skip_storage_marker_set_by_filter_leaves_no_row(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        self.mock_http_endpoint("http://example.com/", content="Hello.")

        async def skip_storage(event):
            event.transaction.markers.add(SKIP_STORAGE)

        dispatcher.add_listener(EVENT_FILTER_PROXY_REQUEST, skip_storage)

        await self.call_controller(
            dispatcher=dispatcher,
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
        )

        assert len(await sql_storage.get_transaction_list(username="anonymous", with_messages=True)) == 0

    @respx.mock
    async def test_body_over_the_recording_cap_is_stored_truncated_and_marked(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        self.mock_http_endpoint("http://example.com/", content="0123456789")

        _, response = await self.call_controller(
            self.create_controller(dispatcher=dispatcher, max_recorded_body_size=4),
            dispatcher=dispatcher,
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
        )

        assert response.body == b"0123456789"
        transaction, _, recorded = await self._find_one_transaction_with_messages_from_storage(sql_storage)
        assert (await blob_storage.get(recorded.body)).data == b"0123"
        assert transaction.markers == {TRUNCATED_RESPONSE_BODY}

    @respx.mock
    async def test_request_body_over_the_recording_cap_is_stored_truncated_and_marked(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        route = respx.post("http://example.com/").mock(return_value=Response(200, content=b"ok"))

        await self.call_controller(
            self.create_controller(dispatcher=dispatcher, max_recorded_body_size=4),
            dispatcher=dispatcher,
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
            method="POST",
            body=b"0123456789",
        )

        assert route.calls.last.request.content == b"0123456789"
        transaction, recorded, _ = await self._find_one_transaction_with_messages_from_storage(sql_storage)
        assert (await blob_storage.get(recorded.body)).data == b"0123"
        assert transaction.markers == {TRUNCATED_REQUEST_BODY}

    @respx.mock
    async def test_request_body_of_exactly_the_recording_cap_is_stored_whole_and_unmarked(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        respx.post("http://example.com/").mock(return_value=Response(200, content=b"ok"))

        await self.call_controller(
            self.create_controller(dispatcher=dispatcher, max_recorded_body_size=4),
            dispatcher=dispatcher,
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
            method="POST",
            body=b"0123",
        )

        transaction, recorded, _ = await self._find_one_transaction_with_messages_from_storage(sql_storage)
        assert (await blob_storage.get(recorded.body)).data == b"0123"
        assert transaction.markers == set()

    @respx.mock
    async def test_request_body_one_byte_over_the_recording_cap_is_stored_truncated_and_marked(
        self, dispatcher: IAsyncEventDispatcher, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        respx.post("http://example.com/").mock(return_value=Response(200, content=b"ok"))

        await self.call_controller(
            self.create_controller(dispatcher=dispatcher, max_recorded_body_size=4),
            dispatcher=dispatcher,
            engine=sql_storage.engine,
            sql_storage=sql_storage,
            blob_storage=blob_storage,
            method="POST",
            body=b"01234",
        )

        transaction, recorded, _ = await self._find_one_transaction_with_messages_from_storage(sql_storage)
        assert (await blob_storage.get(recorded.body)).data == b"0123"
        assert transaction.markers == {TRUNCATED_REQUEST_BODY}
