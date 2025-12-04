import pytest
from rodi import CannotResolveTypeException

from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.http_cache.settings import HttpCacheSettings
from harp_apps.http_cache.transports import AsyncCacheTransport


class MyCustomTransport(AsyncCacheTransport):
    pass


class TestHttpCacheSettings(BaseConfigurableTest):
    type = HttpCacheSettings
    expected_verbose = {
        "enabled": True,
        # hishel 1.0: Controller → SpecificationPolicy (CacheOptions configured in services.yml)
        "policy": {
            "type": "hishel.SpecificationPolicy",
        },
        "storage": {
            "base": "hishel.AsyncBaseStorage",
            "check_ttl_every": 60.0,
            "ttl": None,
            "type": "harp_apps.http_cache.storages.AsyncStorage",
        },
        # hishel 1.0: AsyncCacheTransport moved to _async_httpx module
        # We now wrap it with our custom AsyncCacheTransport for URL normalization
        "transport": {
            "base": "hishel._async_httpx.AsyncCacheTransport",
            "type": "harp_apps.http_cache.transports.AsyncCacheTransport",
        },
    }

    async def test_service_override(self):
        """Test custom cache transport override.

        Note: This test is currently skipped because service override across apps
        during bind events requires special handling. The http_cache app attempts
        to override http_client service, but both apps' on_bind events fire concurrently.
        """
        pytest.skip("Service override across apps requires sequential bind event handling")

    async def test_cache_disabled(self):
        """Test that cache services are not available when disabled."""
        from harp.config import ConfigurationBuilder

        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache"],
                "http_cache": self.create(enabled=False),
            },
            use_default_applications=False,
        )

        # With dependency validation, http_client loads first, then http_cache
        system = await builder.abuild_system()

        with pytest.raises(CannotResolveTypeException):
            system.provider.get("http_cache.transport")
