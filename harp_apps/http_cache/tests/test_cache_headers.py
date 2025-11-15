"""
Tests for cache debugging headers (X-Cache and Age).
"""

import pytest

from harp.config import ConfigurationBuilder
from harp.utils.testing.communicators import ASGICommunicator


class TestCacheHeaders:
    """
    Test that cached responses include debugging headers.
    """

    @pytest.fixture
    async def kernel(self, test_api):
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.applications.add("http_cache", autoload_dependencies=True)  # Auto-loads http_client dependency
        builder.applications.add("proxy")
        builder.applications.add("storage")
        builder.add_values(
            {
                "proxy": {
                    "endpoints": [
                        {
                            "port": 80,
                            "name": "test",
                            "url": test_api.url,
                        }
                    ]
                }
            }
        )

        system = await builder.abuild_system()

        try:
            yield system.asgi_app
        finally:
            await system.dispose()

    @pytest.fixture
    async def client(self, kernel):
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client

    @pytest.mark.asyncio
    async def test_first_request_has_x_cache_miss_header(self, client: ASGICommunicator):
        """First request to cacheable endpoint should have X-Cache: MISS header."""
        response = await client.http_get("/cacheable")
        assert response["status"] == 200
        assert response["body"] == b"cacheable content"

        # Check for X-Cache: MISS header
        headers_dict = dict(response["headers"])
        assert b"x-cache" in headers_dict
        assert headers_dict[b"x-cache"] == b"MISS"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Cache not working due to cache key mismatch issue (see #784). "
        "Cache keys include backend URL which changes on each request in test environment."
    )
    async def test_second_request_has_x_cache_hit_header(self, client: ASGICommunicator):
        """Second request to cacheable endpoint should have X-Cache: HIT header."""
        # First request to populate the cache
        response1 = await client.http_get("/cacheable")
        assert response1["status"] == 200
        headers_dict1 = dict(response1["headers"])
        assert headers_dict1[b"x-cache"] == b"MISS"

        # Second request should hit the cache
        response2 = await client.http_get("/cacheable")
        assert response2["status"] == 200
        assert response2["body"] == b"cacheable content"

        # Check for X-Cache: HIT header
        headers_dict2 = dict(response2["headers"])
        assert b"x-cache" in headers_dict2
        assert headers_dict2[b"x-cache"] == b"HIT"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Cache not working due to cache key mismatch issue (see #784). "
        "Cache keys include backend URL which changes on each request in test environment."
    )
    async def test_cached_response_has_age_header(self, client: ASGICommunicator):
        """Cached response should have Age header indicating cache age in seconds."""
        import time

        # First request to populate the cache
        response1 = await client.http_get("/cacheable")
        assert response1["status"] == 200

        # Wait a bit to ensure age > 0
        time.sleep(1)

        # Second request should hit the cache
        response2 = await client.http_get("/cacheable")
        assert response2["status"] == 200

        # Check for Age header
        headers_dict2 = dict(response2["headers"])
        assert b"age" in headers_dict2

        # Age should be at least 1 second (we waited 1 second)
        age = int(headers_dict2[b"age"])
        assert age >= 1
