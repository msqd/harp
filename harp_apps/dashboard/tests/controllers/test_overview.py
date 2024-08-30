from datetime import datetime
from unittest.mock import Mock

import freezegun
import orjson
import pytest
from multidict import MultiDict

from harp.http import HttpRequest
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.dashboard.controllers.overview import OverviewController
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class OverviewControllerTestFixtureMixin:
    @pytest.fixture
    def controller(self, sql_storage):
        return OverviewController(storage=sql_storage, handle_errors=False)


class _Any24IntegerValues(object):
    "A helper object that compares equal to everything."

    def __eq__(self, other):
        return len(other) == 24 and all(lambda x: isinstance(x.get("value"), int) for x in other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<Any24Values>"


Any24IntegerValues = _Any24IntegerValues()

parametrize_with_now = pytest.mark.parametrize(
    "now",
    [
        datetime(2023, 6, 21, 12, 10, 0),
        datetime(2023, 6, 21, 12, 0, 0),
    ],
)


class TestOverviewController(OverviewControllerTestFixtureMixin, StorageTestFixtureMixin):
    @parametrize_with_now
    async def test_get_summary_data_no_transactions(self, controller: OverviewController, now):
        request = Mock(spec=HttpRequest, query=MultiDict())
        with freezegun.freeze_time(now):
            response = await controller.get_summary_data(request)
        assert response == {
            "tpdex": {"data": Any24IntegerValues, "mean": 100},
            "errors": {"data": Any24IntegerValues, "period": "day", "rate": 0},
            "transactions": {"data": Any24IntegerValues, "period": "day", "rate": 0},
        }

    @parametrize_with_now
    async def test_get_summary_data_with_a_few_transactions(
        self, controller: OverviewController, sql_storage: SqlStorage, now
    ):
        with freezegun.freeze_time(now):
            await self.create_transaction(sql_storage)
            await self.create_transaction(sql_storage)
            await self.create_transaction(sql_storage)
        request = Mock(spec=HttpRequest, query=MultiDict())
        with freezegun.freeze_time(now):
            response = await controller.get_summary_data(request)
        assert response == {
            "tpdex": {"data": Any24IntegerValues, "mean": 100},
            "errors": {"data": Any24IntegerValues, "period": "day", "rate": 0},
            "transactions": {"data": Any24IntegerValues, "period": "day", "rate": 3},
        }


class TestOverviewControllerThroughASGI(
    OverviewControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    @parametrize_with_now
    async def test_get_summary_data_with_a_few_transactions_using_asgi(
        self, client: ASGICommunicator, sql_storage: SqlStorage, now
    ):
        with freezegun.freeze_time(now):
            await self.create_transaction(sql_storage)
            await self.create_transaction(sql_storage)
            await self.create_transaction(sql_storage)

            response = await client.http_get("/api/overview/summary")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)

        assert orjson.loads(response["body"]) == {
            "tpdex": {"data": Any24IntegerValues, "mean": 100},
            "errors": {"data": Any24IntegerValues, "period": "day", "rate": "0"},
            "transactions": {"data": Any24IntegerValues, "period": "day", "rate": "3"},
        }
