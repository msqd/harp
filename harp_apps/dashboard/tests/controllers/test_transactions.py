from unittest.mock import ANY, Mock

import orjson
import pytest
from freezegun import freeze_time
from multidict import MultiDict

from harp.http import HttpRequest
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.dashboard.controllers.transactions import TransactionsController
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TransactionsControllerTestFixtureMixin:
    @pytest.fixture
    def controller(self, sql_storage):
        return TransactionsController(storage=sql_storage, handle_errors=False)


class TestTransactionsController(TransactionsControllerTestFixtureMixin, StorageTestFixtureMixin):
    async def test_get_returns_404_when_transaction_not_found(self, controller: TransactionsController):
        request = Mock(spec=HttpRequest, query=MultiDict(), extensions={"user": "anonymous"})
        response = await controller.get(request, "non-existent-id")
        assert response.status == 404

    async def test_filters_using_handler(self, controller: TransactionsController):
        request = Mock(spec=HttpRequest, query=MultiDict())
        response = await controller.filters(request)

        # todo this format may/will change, but we add this test to ensure we start to be meticulous about quality
        assert response == {
            "endpoint": {"current": None, "values": ANY},
            "flag": {"current": None, "values": ANY, "fallbackName": ANY},
            "method": {"current": None, "values": ANY},
            "status": {"current": None, "values": ANY},
            "tpdex": {"current": {"min": ANY, "max": ANY}, "values": ANY},
        }

    async def test_filters_meta_updated(self, controller: TransactionsController):
        with freeze_time("2024-01-01 12:00:00"):
            await self.create_transaction(controller.storage, endpoint="foo")

            request = Mock(spec=HttpRequest, query=MultiDict())
            response = await controller.filters(request)

            assert response["endpoint"]["values"] == [{"count": 1, "name": "foo"}]

            # Create two more transactions
            await self.create_transaction(controller.storage, endpoint="foo")
            await self.create_transaction(controller.storage, endpoint="foo")

        # Check the count again
        with freeze_time("2024-01-01 12:00:20"):
            # Check the count again
            response = await controller.filters(request)
            assert response["endpoint"]["values"] == [{"count": 1, "name": "foo"}]

        # Move forward in time by 2 minutes
        with freeze_time("2024-01-01 12:02:00"):
            # Check the count again
            response = await controller.filters(request)
            assert response["endpoint"]["values"] == [{"count": 3, "name": "foo"}]


class TestTransactionsControllerFlags(TransactionsControllerTestFixtureMixin, StorageTestFixtureMixin):
    def request(self, method):
        return Mock(spec=HttpRequest, method=method, query=MultiDict(), extensions={"user": "anonymous"})

    async def flags_of(self, controller: TransactionsController, transaction_id):
        transaction = await controller.storage.get_transaction(transaction_id, username="anonymous")
        return transaction.extras.get("flags", [])

    async def test_put_flag_twice_keeps_one_flag(self, controller: TransactionsController):
        transaction = await self.create_transaction(controller.storage)

        first = await controller.set_user_flag(self.request("PUT"), transaction.id, "favorite")
        second = await controller.set_user_flag(self.request("PUT"), transaction.id, "favorite")

        assert first.status == 200
        assert second.status == 200
        assert await self.flags_of(controller, transaction.id) == ["favorite"]

    async def test_delete_removes_only_the_named_flag(self, controller: TransactionsController, monkeypatch):
        from harp_apps.storage.models import flags

        monkeypatch.setitem(flags.FLAGS_BY_NAME, "other", 2)
        monkeypatch.setitem(flags.FLAGS_BY_TYPE, 2, "other")
        transaction = await self.create_transaction(controller.storage)
        await controller.set_user_flag(self.request("PUT"), transaction.id, "favorite")
        await controller.set_user_flag(self.request("PUT"), transaction.id, "other")

        response = await controller.set_user_flag(self.request("DELETE"), transaction.id, "other")

        assert response.status == 200
        assert await self.flags_of(controller, transaction.id) == ["favorite"]

    async def test_delete_flag_not_set_answers_2xx(self, controller: TransactionsController):
        transaction = await self.create_transaction(controller.storage)

        response = await controller.set_user_flag(self.request("DELETE"), transaction.id, "favorite")

        assert response.status == 200

    async def test_unknown_flag_answers_400(self, controller: TransactionsController):
        transaction = await self.create_transaction(controller.storage)

        response = await controller.set_user_flag(self.request("PUT"), transaction.id, "nope")

        assert response.status == 400

    async def test_unknown_transaction_answers_404(self, controller: TransactionsController):
        for method in ("PUT", "DELETE"):
            response = await controller.set_user_flag(self.request(method), "missing", "favorite")
            assert response.status == 404


class TestTransactionsControllerThroughASGI(
    TransactionsControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    async def test_filters_using_asgi(self, client: ASGICommunicator):
        # todo this is probably not the right place, we're unit testing a controller, should we really duplicate tests
        # to also go through asgi ? Let's think about this, there is no real value of aving two tests doing the same
        # with an additional layer here.
        response = await client.http_get("/api/transactions/filters")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)

        # todo this format may/will change, but we add this test to ensure we start to be meticulous about quality
        assert orjson.loads(response["body"]) == {
            "endpoint": {"current": None, "values": ANY},
            "flag": {"current": None, "values": ANY, "fallbackName": ANY},
            "method": {"current": None, "values": ANY},
            "status": {"current": None, "values": ANY},
            "tpdex": {"current": {"min": ANY, "max": ANY}, "values": ANY},
        }
