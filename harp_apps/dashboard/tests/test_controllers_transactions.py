from unittest.mock import ANY, Mock

import orjson
import pytest
from multidict import MultiDict

from harp.core.asgi import ASGIRequest
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin

from ..controllers.transactions import TransactionsController


class TransactionsControllerFixtureMixin:
    @pytest.fixture
    def controller(self, storage):
        return TransactionsController(storage=storage, handle_errors=False)


class TestTransactionsController(
    TransactionsControllerFixtureMixin,
    SqlalchemyStorageTestFixtureMixin,
):
    async def test_filters_using_handler(self, controller: TransactionsController):
        request = Mock(
            spec=ASGIRequest,
            query=MultiDict(),
        )

        response = await controller.filters(request, None)

        # todo this format may/will change, but we add this test to ensure we start to be meticulous about quality
        assert response == {
            "endpoint": {"current": None, "values": ANY},
            "flag": {"current": None, "values": ANY},
            "method": {"current": None, "values": ANY},
            "status": {"current": None, "values": ANY},
        }


class TestTransactionsControllerThroughASGI(
    TransactionsControllerFixtureMixin,
    SqlalchemyStorageTestFixtureMixin,
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
            "flag": {"current": None, "values": ANY},
            "method": {"current": None, "values": ANY},
            "status": {"current": None, "values": ANY},
        }