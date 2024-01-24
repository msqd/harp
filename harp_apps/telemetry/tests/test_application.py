from unittest.mock import ANY

import orjson
import pytest
import respx
from httpx import AsyncClient, Response
from rodi import Container
from whistle import AsyncEventDispatcher

from harp.config.events import EVENT_FACTORY_BOUND, FactoryBoundEvent
from harp.typing import GlobalSettings
from harp.utils.testing.applications import BaseTestForApplications


class TestTelemetryApplication(BaseTestForApplications):
    name = "harp_apps.telemetry"

    @respx.mock
    @pytest.mark.parametrize("url", [None, "https://example.com/"])
    async def test_endpoints(self, ApplicationType, url):
        endpoint = respx.post(url).mock(return_value=Response(201, content=b"{}"))

        application = ApplicationType(endpoint=url)
        assert application.endpoint == url or application.default_endpoint

        response = await application.ping(AsyncClient(), applications="foo,bar")
        assert endpoint.called and endpoint.call_count == 1
        assert response.status_code == 201
        assert orjson.loads(endpoint.calls.last.request.content) == {
            "f": ANY,
            "a": "foo,bar",
            "v": ANY,
            "c": 1,
        }

    @respx.mock
    @pytest.mark.parametrize("url", [None, "https://example.com/"])
    async def test_events(self, ApplicationType, url):
        endpoint = respx.post(url).mock(return_value=Response(201, content=b"{}"))
        application = ApplicationType(endpoint=url)

        dispatcher = AsyncEventDispatcher()
        application.register_events(dispatcher)

        container = Container()
        container.add_instance({"applications": ["oh", "my"]}, GlobalSettings)
        container.add_instance(AsyncClient())

        provider = container.build_provider()

        assert not endpoint.called
        await dispatcher.adispatch(EVENT_FACTORY_BOUND, FactoryBoundEvent(provider, None))

        assert endpoint.called and endpoint.call_count == 1
        assert endpoint.calls.last.request.url == url or application.default_endpoint
        assert endpoint.calls.last.request.method == "POST"
        assert orjson.loads(endpoint.calls.last.request.content) == {
            "f": ANY,
            "a": "oh,my",
            "v": ANY,
            "c": 1,
        }
