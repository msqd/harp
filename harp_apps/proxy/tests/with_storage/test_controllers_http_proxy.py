from typing import cast
from unittest.mock import ANY, AsyncMock, patch

import pytest
import respx
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.config.asdict import asdict
from harp.http import HttpRequest, HttpResponse
from harp.utils.bytes import ensure_bytes
from harp.utils.testing.mixins import ControllerTestFixtureMixin
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_TRANSACTION_STARTED
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.services.sql import SqlStorage
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
        with patch("harp_apps.proxy.controllers.HttpProxyController.user_agent", "test/1.0"):
            yield

    def mock_http_endpoint(self, url, /, *, status=200, content=""):
        """Make sure you decorate your tests function using this with respx.mock decorator, otherwise the real network
        will be called and you may have some headaches..."""
        return respx.get(url).mock(return_value=Response(status, content=ensure_bytes(content)))

    def create_controller(
        self,
        url=None,
        *args,
        dispatcher: IAsyncEventDispatcher,
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
        assert request_headers.data == b"host: example.com\nuser-agent: test/1.0"
        assert request_headers.content_type == "http/headers"
        assert (await blob_storage.get(request.body)).data == b""
        assert asdict(request) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "a11eda99171248663db8cf2ef3857f52a974ba94",
            "body": "adc83b19e793491b1c6ea0fd8b46cd9f32e592fc",
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
            "headers": "916ef336ce8ac9a91de41ce88c4b4bfc747b3ac9",
            "body": "6ffdd89703735cc316470566467b816446f008ce",
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
            "extras": {
                "flags": [],
                "method": "GET",
                "status_class": "2xx",
                "cached": False,
                "no_cache": False,
            },
        }

        request_headers = await blob_storage.get(request.headers)
        assert request_headers.data == (
            b"accept: application/json\nvary: custom\nhost: example.com\nuser-agent: test/1.0"
        )
        assert request_headers.content_type == "http/headers"
        assert (await blob_storage.get(request.body)).data == b""
        assert asdict(request) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "74c903b455127bd235bb06e9e84151e9535c6389",
            "body": "adc83b19e793491b1c6ea0fd8b46cd9f32e592fc",
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
            "headers": "916ef336ce8ac9a91de41ce88c4b4bfc747b3ac9",
            "body": "6ffdd89703735cc316470566467b816446f008ce",
            "created_at": ANY,
        }
