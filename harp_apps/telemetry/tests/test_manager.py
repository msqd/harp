from typing import cast
from unittest.mock import ANY, AsyncMock

import orjson
import pytest
import respx
from httpx import AsyncClient, Response
from whistle import AsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_STARTED
from harp.typing import GlobalSettings
from harp_apps.telemetry.manager import TelemetryManager

stub_settings = cast(GlobalSettings, {"applications": ["oh", "my"]})


class MockedTelemetryManager(TelemetryManager):
    start = AsyncMock()


class TestTelemetryManager:
    async def test_events(self):
        dispatcher = AsyncEventDispatcher()
        assert not dispatcher.has_listeners(EVENT_CORE_STARTED)
        manager = MockedTelemetryManager(stub_settings, AsyncClient(), None, dispatcher)
        assert dispatcher.has_listeners(EVENT_CORE_STARTED)

        assert not manager.start.called
        await dispatcher.adispatch(EVENT_CORE_STARTED)
        assert manager.start.called and manager.start.call_count == 1

    @respx.mock
    @pytest.mark.parametrize("url", [None, "https://example.com/"])
    async def test_ping(self, url):
        endpoint = respx.post(url).mock(return_value=Response(201, content=b"{}"))

        manager = TelemetryManager(stub_settings, AsyncClient(), endpoint=url)

        assert not endpoint.called

        await manager.ping()

        assert endpoint.called and endpoint.call_count == 1
        assert endpoint.calls.last.request.url == (url or manager.default_endpoint)
        assert endpoint.calls.last.request.method == "POST"
        assert orjson.loads(endpoint.calls.last.request.content) == {
            "f": ANY,
            "a": "oh,my",
            "v": ANY,
            "c": 0,
            "i": 0,
            "t": "start",
        }
        assert manager.count == 1
