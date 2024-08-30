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
