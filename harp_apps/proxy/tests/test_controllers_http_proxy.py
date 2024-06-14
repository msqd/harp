from unittest.mock import ANY, AsyncMock, patch

import pytest
import respx
from httpx import AsyncClient, Response
from whistle import AsyncEventDispatcher

from harp.utils.bytes import ensure_bytes
from harp.utils.testing.mixins import ControllerTestFixtureMixin
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin

from ..controllers import HttpProxyController
from ..events import EVENT_TRANSACTION_STARTED


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

    def mock_http_endpoint(self, database_url, /, *, status=200, content=""):
        """Make sure you decorate your tests function using this with respx.mock decorator, otherwise the real network
        will be called and you may have some headaches..."""
        return respx.get(database_url).mock(return_value=Response(status, content=ensure_bytes(content)))

    def create_controller(self, url=None, *args, http_client=None, **kwargs):
        return super().create_controller(
            url or "http://example.com/", *args, http_client=http_client or AsyncClient(), **kwargs
        )


class TestHttpProxyController(HttpProxyControllerTestFixtureMixin, DispatcherTestFixtureMixin):
    @respx.mock
    async def test_basic_get(self):
        endpoint = self.mock_http_endpoint("http://example.com/", content="Hello.")
        request, response = await self.call_controller(self.create_controller("http://example.com/"))

        # check output and side effects
        assert endpoint.called and endpoint.call_count == 1
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b"Hello."

    @respx.mock
    async def test_get_with_tags(self, dispatcher: AsyncEventDispatcher):
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
    SqlalchemyStorageTestFixtureMixin,
    DispatcherTestFixtureMixin,
):
    async def _find_one_transaction_with_messages_from_storage(self, storage):
        # get transaction, request and response
        transactions = await storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        transaction = transactions[0]
        return transaction, transaction.messages[0], transaction.messages[1]

    @respx.mock
    async def test_basic_get(self, storage: SqlAlchemyStorage):
        self.mock_http_endpoint("http://example.com/", content="Hello.")

        # register the storage
        await self.call_controller(self.create_controller("http://example.com/", dispatcher=storage._dispatcher))
        await storage.wait_for_background_tasks_to_be_processed()

        transaction, request, response = await self._find_one_transaction_with_messages_from_storage(storage)

        # transaction
        assert transaction.to_dict(omit_none=False) == {
            "id": ANY,
            "type": "http",
            "endpoint": None,
            "elapsed": ANY,
            "tpdex": ANY,
            "started_at": ANY,
            "finished_at": ANY,
            "messages": ANY,
            "tags": {},
            "extras": {"flags": [], "method": "GET", "status_class": "2xx", "cached": False, "no_cache": False},
        }

        # request
        assert (await storage.get_blob(request.headers)).data == b"host: example.com\nuser-agent: test/1.0"
        assert (await storage.get_blob(request.body)).data == b""
        assert request.to_dict(omit_none=False) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "ecd46dd3023926417e1205b219aec4c2b9e0dab0",
            "body": "adc83b19e793491b1c6ea0fd8b46cd9f32e592fc",
            "created_at": ANY,
        }

        # response
        assert (await storage.get_blob(response.headers)).data == b""
        assert (await storage.get_blob(response.body)).data == b"Hello."
        assert response.to_dict(omit_none=False) == {
            "id": 2,
            "transaction_id": ANY,
            "kind": "response",
            "summary": "HTTP/1.1 200 OK",
            "headers": "7507b0bca78329128f61f37d09c88b8712cecd64",
            "body": "6ffdd89703735cc316470566467b816446f008ce",
            "created_at": ANY,
        }

    @respx.mock
    async def test_get_with_tags(self, storage):
        self.mock_http_endpoint("http://example.com/", content="Hello.")

        # call our controller
        await self.call_controller(
            self.create_controller("http://example.com/", dispatcher=storage._dispatcher),
            headers={
                "x-harp-foo": "bar",
                "accept": "application/json",
                "vary": "custom",
            },
        )
        await storage.wait_for_background_tasks_to_be_processed()

        transaction, request, response = await self._find_one_transaction_with_messages_from_storage(storage)

        assert transaction.to_dict(omit_none=False) == {
            "id": ANY,
            "type": "http",
            "endpoint": None,
            "elapsed": ANY,
            "tpdex": ANY,
            "started_at": ANY,
            "finished_at": ANY,
            "messages": ANY,
            "tags": {"foo": "bar"},
            "extras": {"flags": [], "method": "GET", "status_class": "2xx", "cached": False, "no_cache": False},
        }

        assert (await storage.get_blob(request.headers)).data == (
            b"accept: application/json\nvary: custom\nhost: example.com\nuser-agent: test/1.0"
        )
        assert (await storage.get_blob(request.body)).data == b""
        assert request.to_dict(omit_none=False) == {
            "id": 1,
            "transaction_id": ANY,
            "kind": "request",
            "summary": "GET / HTTP/1.1",
            "headers": "885ad9e4633a3c038f13c32e4ee48fc9221c0152",
            "body": "adc83b19e793491b1c6ea0fd8b46cd9f32e592fc",
            "created_at": ANY,
        }

        assert (await storage.get_blob(response.headers)).data == b""
        assert (await storage.get_blob(response.body)).data == b"Hello."
        assert response.to_dict(omit_none=False) == {
            "id": 2,
            "transaction_id": ANY,
            "kind": "response",
            "summary": "HTTP/1.1 200 OK",
            "headers": "7507b0bca78329128f61f37d09c88b8712cecd64",
            "body": "6ffdd89703735cc316470566467b816446f008ce",
            "created_at": ANY,
        }
