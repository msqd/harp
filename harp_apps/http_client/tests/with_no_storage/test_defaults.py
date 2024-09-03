from unittest.mock import AsyncMock

import respx
from httpx import AsyncClient, Response

from harp.config.asdict import asdict
from harp_apps.http_client.contrib.hishel.storages import AsyncStorage
from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, EVENT_FILTER_HTTP_CLIENT_RESPONSE
from harp_apps.http_client.tests._base import BaseTestDefaultsWith
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://www.example.com/"


class TestDefaultsWithNoStorage(BaseTestDefaultsWith):
    async def test_defaults(self):
        system = await self.create_system()

        assert asdict(system.config) == {
            "applications": ["harp_apps.http_client"],
            "http_client": {},
        }
        assert asdict(system.config, verbose=True) == {
            "applications": ["harp_apps.http_client"],
            "http_client": {
                "cache": {
                    "controller": {
                        "allow_heuristics": False,
                        "allow_stale": False,
                        "cacheable_methods": ["GET", "HEAD"],
                        "cacheable_status_codes": [
                            200,
                            203,
                            204,
                            206,
                            300,
                            301,
                            308,
                            404,
                            405,
                            410,
                            414,
                            501,
                        ],
                        "type": "hishel.Controller",
                    },
                    "enabled": True,
                    "storage": {
                        "base": "hishel.AsyncBaseStorage",
                        "check_ttl_every": 60.0,
                        "ttl": None,
                        "type": "harp_apps.http_client.contrib.hishel.storages.AsyncStorage",
                    },
                    "transport": {"type": "hishel.AsyncCacheTransport"},
                },
                "proxy_transport": {"type": "harp_apps.http_client.transport.AsyncFilterableTransport"},
                "timeout": 30.0,
                "transport": {
                    "retries": 0,
                    "type": "httpx.AsyncHTTPTransport",
                    "verify": True,
                },
                "type": "httpx.AsyncClient",
            },
        }

        storage = system.provider.get("http_client.cache.storage")
        assert isinstance(storage, AsyncStorage)
        assert isinstance(storage._storage, MemoryBlobStorage)

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
