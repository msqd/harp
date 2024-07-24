from unittest.mock import ANY, AsyncMock

import respx
from httpx import AsyncClient, Response

from harp.config import asdict
from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, EVENT_FILTER_HTTP_CLIENT_RESPONSE
from harp_apps.http_client.tests._base import BaseTestDefaultsWith
from harp_apps.storage.types import IBlobStorage

URL = "http://www.example.com/"


class TestDefaultsWithNoStorage(BaseTestDefaultsWith):
    async def test_defaults(self):
        system = await self.create_system()

        assert asdict(system.config) == {
            "applications": ["harp_apps.http_client"],
            "http_client": {
                "cache": {
                    "enabled": True,
                    "controller": ANY,
                    "storage": ANY,
                    "transport": {"@type": ANY},
                    "ttl": ANY,
                    "check_ttl_every": ANY,
                },
                "timeout": 30.0,
                "transport": {"@type": "httpx:AsyncHTTPTransport"},
            },
        }

        assert type(system.provider.get(IBlobStorage)).__name__ == "NullBlobStorage"

    @respx.mock
    async def test_events(self):
        system = await self.create_system()
        endpoint = respx.get(URL).mock(return_value=Response(200, content=b"Hello, world."))
        http_client = system.provider.get(AsyncClient)

        # register events
        on_filter_request, on_filter_response = AsyncMock(), AsyncMock()
        system.dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, on_filter_request)
        system.dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, on_filter_response)

        # simple request
        response = await http_client.get(URL)
        assert endpoint.called
        assert response.status_code == 200
        assert on_filter_request.called
        assert on_filter_response.called
