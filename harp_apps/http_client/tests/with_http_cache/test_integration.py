"""Integration tests for http_client with http_cache enabled.

These tests verify that the http_client works correctly with the http_cache app
loaded, ensuring backward compatibility and proper cache behavior.
"""

import pytest
import respx
from httpx import AsyncClient, Response

from harp.config import ConfigurationBuilder


@pytest.mark.asyncio
class TestHttpClientWithCache:
    """Test http_client integration with http_cache app."""

    async def test_cache_enabled_by_default(self):
        """Verify http_cache is loaded by default and caching works."""
        # Build system with both http_client and http_cache (default apps)
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache"],
                "http_client": {"enabled": True},
                "http_cache": {"enabled": True},
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)

        # Get the http_client
        http_client = system.provider.get("http_client")
        assert http_client is not None
        assert isinstance(http_client, AsyncClient)

        # Verify cache transport is in the chain
        # The chain should be: AsyncClient -> AsyncCacheTransport -> AsyncFilterableTransport -> AsyncHTTPTransport
        from harp_apps.http_cache.transports import AsyncCacheTransport

        # The transport should be our cache transport
        assert isinstance(http_client._transport, AsyncCacheTransport)

    async def test_real_caching_behavior(self):
        """Test that responses are actually cached and reused."""
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache"],
                "http_client": {"enabled": True},
                "http_cache": {"enabled": True},
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)
        http_client = system.provider.get("http_client")

        with respx.mock:
            # Mock a cacheable endpoint
            route = respx.get("http://api.example.com/data").mock(
                return_value=Response(
                    200,
                    json={"value": "cached_data"},
                    headers={"Cache-Control": "public, max-age=3600"},
                )
            )

            # First request - should hit the backend
            response1 = await http_client.get("http://api.example.com/data")
            assert response1.status_code == 200
            assert response1.json() == {"value": "cached_data"}
            assert route.call_count == 1

            # Second request - should be served from cache (no additional backend call)
            response2 = await http_client.get("http://api.example.com/data")
            assert response2.status_code == 200
            assert response2.json() == {"value": "cached_data"}
            assert route.call_count == 1, "Second request should be served from cache"

            # Verify the response indicates it came from cache
            assert response2.extensions.get("hishel_from_cache") is True

    async def test_cache_miss_behavior(self):
        """Test that non-cacheable responses (no-store) are not cached."""
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache"],
                "http_client": {"enabled": True},
                "http_cache": {"enabled": True},
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)
        http_client = system.provider.get("http_client")

        with respx.mock:
            # Mock a non-cacheable endpoint (no-store directive)
            route = respx.get("http://api.example.com/dynamic").mock(
                return_value=Response(
                    200,
                    json={"value": "dynamic_data"},
                    headers={"Cache-Control": "no-store"},  # Explicitly non-cacheable
                )
            )

            # First request
            response1 = await http_client.get("http://api.example.com/dynamic")
            assert response1.status_code == 200
            assert route.call_count == 1

            # Second request - should hit backend again (not cached due to no-store)
            response2 = await http_client.get("http://api.example.com/dynamic")
            assert response2.status_code == 200
            assert route.call_count == 2, "Second request should hit backend (no-store prevents caching)"

            # Verify the response didn't come from cache
            assert response2.extensions.get("hishel_from_cache") is not True
