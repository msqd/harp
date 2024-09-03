import hishel
import httpx
from httpx import AsyncClient

from harp.config import ConfigurationBuilder
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.http_client.settings import CacheSettings, HttpClientSettings
from harp_apps.http_client.transport import AsyncFilterableTransport


class BaseHttpClientSettingsTest(BaseConfigurableTest):
    type = HttpClientSettings

    async def create_system(self, settings: HttpClientSettings, /):
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client"],
                "http_client": settings,
            },
            use_default_applications=False,
        )

        return await builder.abuild_system()


class TestHttpClientSettings(BaseHttpClientSettingsTest):
    expected_verbose = {
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
        "transport": {"retries": 0, "type": "httpx.AsyncHTTPTransport", "verify": True},
        "type": "httpx.AsyncClient",
    }

    async def test_without_cache(self):
        settings = self.create(cache={"enabled": False})
        assert settings.cache.enabled is False

        system = await self.create_system(settings)
        assert system.config["http_client"].cache.enabled is False

        http_client = system.provider.get("http_client")
        assert http_client is system.provider.get(AsyncClient)
        assert isinstance(http_client._transport, AsyncFilterableTransport)
        assert isinstance(http_client._transport._transport, httpx.AsyncHTTPTransport)

    async def test_without_cache_with_custom_client(self):
        settings = self.create(
            transport={"type": "httpx._client.BaseClient", "arguments": {}},
            cache={"enabled": False},
        )
        assert settings.cache.enabled is False

        system = await self.create_system(settings)
        http_client = system.provider.get("http_client")

        assert isinstance(http_client._transport._transport, httpx._client.BaseClient)

    async def test_with_default_cache(self):
        settings = self.create()

        assert settings.cache.enabled is True
        assert isinstance(settings.cache, CacheSettings)

        system = await self.create_system(settings)
        http_client = system.provider.get("http_client")

        assert type(http_client._transport).__name__ == "AsyncCacheTransport"
        assert http_client._transport._controller._allow_heuristics is False
        assert http_client._transport._controller._allow_stale is False
        assert http_client._transport._controller._cacheable_methods == ["GET", "HEAD"]
        assert http_client._transport._controller._cacheable_status_codes == list(
            hishel.HEURISTICALLY_CACHEABLE_STATUS_CODES
        )

    async def test_with_custom_cache(self):
        settings = HttpClientSettings(
            cache={
                "enabled": True,
                "controller": {
                    "allow_stale": True,
                    "cacheable_methods": ["GET"],
                    "cacheable_status_codes": [200],
                },
            }
        )

        assert settings.cache.enabled is True
        assert isinstance(settings.cache, CacheSettings)

        system = await self.create_system(settings)
        http_client = system.provider.get("http_client")

        assert type(http_client._transport).__name__ == "AsyncCacheTransport"

        assert isinstance(http_client._transport._controller, hishel.Controller)
        assert http_client._transport._controller._allow_heuristics is False
        assert http_client._transport._controller._allow_stale is True
        assert http_client._transport._controller._cacheable_methods == ["GET"]
        assert http_client._transport._controller._cacheable_status_codes == [200]
