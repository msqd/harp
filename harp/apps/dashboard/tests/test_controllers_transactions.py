from unittest.mock import ANY, Mock

import orjson
import pytest
from multidict import MultiDict

from harp.apps.dashboard.controllers.transactions import TransactionsController
from harp.contrib.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageFixtureMixin
from harp.core.asgi import ASGIKernel, ASGIRequest
from harp.core.asgi.resolvers import ControllerResolver
from harp.core.views.json import register as register_json_views
from harp.utils.testing.communicators import ASGICommunicator


class TestControllerTransactions(SqlalchemyStorageFixtureMixin):
    @pytest.fixture
    def controller(self, storage):
        return TransactionsController(storage=storage, handle_errors=False)

    @pytest.fixture
    async def client(self, controller):
        kernel = ASGIKernel(resolver=ControllerResolver(default_controller=controller), handle_errors=False)
        register_json_views(kernel.dispatcher)
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client

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
