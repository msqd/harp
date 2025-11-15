import httpx
from httpx import AsyncClient

from harp.config import ConfigurationBuilder
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.http_client.settings import HttpClientSettings
from harp_apps.http_client.transports import AsyncFilterableTransport


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

        return await builder.abuild_system(validate_dependencies=False)


class TestHttpClientSettings(BaseHttpClientSettingsTest):
    expected_verbose = {
        "enabled": True,
        "proxy_transport": {"type": "harp_apps.http_client.transports.AsyncFilterableTransport"},
        "timeout": 30.0,
        "transport": {"retries": 0, "type": "httpx.AsyncHTTPTransport", "verify": True},
        "type": "httpx.AsyncClient",
    }

    async def test_default_settings(self):
        """Test http_client with default settings (no cache)."""
        settings = self.create()

        system = await self.create_system(settings)

        http_client = system.provider.get("http_client")
        assert http_client is system.provider.get(AsyncClient)
        assert isinstance(http_client._transport, AsyncFilterableTransport)
        assert isinstance(http_client._transport._transport, httpx.AsyncHTTPTransport)

    async def test_with_custom_transport(self):
        """Test http_client with custom transport."""
        settings = self.create(
            transport={"type": "httpx._client.BaseClient", "arguments": {}},
        )

        system = await self.create_system(settings)
        http_client = system.provider.get("http_client")

        assert isinstance(http_client._transport._transport, httpx._client.BaseClient)
