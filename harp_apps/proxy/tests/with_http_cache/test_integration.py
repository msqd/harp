"""Integration tests for proxy with http_cache enabled.

These tests verify end-to-end caching behavior through the proxy layer.
"""

import pytest
import respx
from httpx import Response

from harp.config import ConfigurationBuilder
from harp.utils.testing.communicators import ASGICommunicator


@pytest.mark.asyncio
class TestProxyWithHttpCache:
    """Test proxy integration with http_cache app for end-to-end caching."""

    async def test_proxy_with_cache_enabled(self):
        """Verify that proxy works with http_cache and requests are cached."""
        # Build system with proxy, http_client, and http_cache
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache", "proxy"],
                "http_client": {"enabled": True},
                "http_cache": {"enabled": True},
                "proxy": {
                    "enabled": True,
                    "endpoints": [{"name": "api", "port": 80, "url": "http://api.example.com/"}],
                },
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)
        app = system.asgi_app

        with respx.mock:
            # Mock a cacheable endpoint
            route = respx.get("http://api.example.com/data").mock(
                return_value=Response(
                    200,
                    json={"value": "test"},
                    headers={"Cache-Control": "public, max-age=3600"},
                )
            )

            # First request through proxy - should hit backend
            communicator = ASGICommunicator(app)
            await communicator.asgi_lifespan_startup()
            response1 = await communicator.http_get("/data", headers=[(b"x-harp-endpoint", b"api")])
            assert response1["status"] == 200
            assert route.call_count == 1

            # Second request through proxy - should be served from cache
            response2 = await communicator.http_get("/data", headers=[(b"x-harp-endpoint", b"api")])
            assert response2["status"] == 200
            assert route.call_count == 1, "Should not hit backend again (cached)"

    async def test_proxy_without_http_cache_app(self):
        """Verify that proxy works correctly without http_cache app loaded.

        This ensures cache logic is not applied when http_cache is not enabled.
        """
        # Build system WITHOUT http_cache
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "proxy"],  # NO http_cache
                "http_client": {"enabled": True},
                "proxy": {
                    "enabled": True,
                    "endpoints": [{"name": "api", "port": 80, "url": "http://api.example.com/"}],
                },
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)
        app = system.asgi_app

        with respx.mock:
            route = respx.get("http://api.example.com/test").mock(
                return_value=Response(
                    200,
                    json={"value": "test"},
                    headers={"Cache-Control": "public, max-age=3600"},
                )
            )

            # Make two requests
            communicator = ASGICommunicator(app)
            await communicator.asgi_lifespan_startup()
            _response1 = await communicator.http_get("/test", headers=[(b"x-harp-endpoint", b"api")])
            _response2 = await communicator.http_get("/test", headers=[(b"x-harp-endpoint", b"api")])

            # Both should hit backend (no caching without http_cache app)
            assert route.call_count == 2, "Without http_cache, all requests should hit backend"

    async def test_proxy_cache_different_endpoints(self):
        """Verify cache isolation between different proxy endpoints."""
        builder = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache", "proxy"],
                "http_client": {"enabled": True},
                "http_cache": {"enabled": True},
                "proxy": {
                    "enabled": True,
                    "endpoints": [
                        {"name": "api1", "port": 8001, "url": "http://api1.example.com/"},
                        {"name": "api2", "port": 8002, "url": "http://api2.example.com/"},
                    ],
                },
            },
            use_default_applications=False,
        )

        system = await builder.abuild_system(validate_dependencies=False)
        app = system.asgi_app

        with respx.mock:
            # Mock same path on different backends
            route1 = respx.get("http://api1.example.com/data").mock(
                return_value=Response(200, json={"source": "api1"}, headers={"Cache-Control": "public, max-age=3600"})
            )

            route2 = respx.get("http://api2.example.com/data").mock(
                return_value=Response(200, json={"source": "api2"}, headers={"Cache-Control": "public, max-age=3600"})
            )

            communicator = ASGICommunicator(app)
            await communicator.asgi_lifespan_startup()

            # Request to api1 (port 8001)
            response1 = await communicator.http_get("/data", port=8001)
            assert response1["status"] == 200
            assert route1.call_count == 1

            # Request to api2 (port 8002) - should not use api1's cache
            response2 = await communicator.http_get("/data", port=8002)
            assert response2["status"] == 200
            assert route2.call_count == 1

            # Second request to api1 - should use cache
            _response3 = await communicator.http_get("/data", port=8001)
            assert route1.call_count == 1, "api1 second request should be cached"

            # Second request to api2 - should use cache
            _response4 = await communicator.http_get("/data", port=8002)
            assert route2.call_count == 1, "api2 second request should be cached"
