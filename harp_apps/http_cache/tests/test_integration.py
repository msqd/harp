"""Integration tests for normalized cache transport with load balancing."""

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, Response, AsyncHTTPTransport

from harp_apps.http_cache.transports import AsyncCacheTransport


@pytest.mark.asyncio
class TestLoadBalancingCacheIntegration:
    """Test cache behavior with load-balanced backends."""

    async def test_cache_hit_across_backends(self, mock_storage):
        """Verify cache hit when switching between load-balanced backends."""
        storage = mock_storage
        policy = SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET"], allow_stale=False)
        )

        # Create transport with our normalized cache
        # The transport needs a next_transport to forward requests to
        next_transport = AsyncHTTPTransport()
        transport = AsyncCacheTransport(next_transport=next_transport, storage=storage, policy=policy)

        # Create client with our transport
        async with AsyncClient(transport=transport) as client:
            # Mock two different backend servers
            with respx.mock:
                # First backend
                route1 = respx.get("http://backend1.example.com/api/data").mock(
                    return_value=Response(
                        200, json={"data": "response"}, headers={"Cache-Control": "public, max-age=3600"}
                    )
                )

                # Second backend (same path, different host)
                route2 = respx.get("http://backend2.example.com/api/data").mock(
                    return_value=Response(
                        200,
                        json={"data": "different"},  # Different data to detect if cache is used
                        headers={"Cache-Control": "public, max-age=3600"},
                    )
                )

                # First request to backend1
                response1 = await client.get("http://backend1.example.com/api/data")
                assert response1.json() == {"data": "response"}
                assert route1.called

                # Second request to backend2 (should use cache, not make request)
                response2 = await client.get("http://backend2.example.com/api/data")
                assert response2.json() == {"data": "response"}
                assert not route2.called

    async def test_cache_miss_different_paths(self, mock_storage):
        """Verify cache miss when paths differ between backends."""
        storage = mock_storage
        policy = SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET"], allow_stale=False)
        )

        next_transport = AsyncHTTPTransport()
        transport = AsyncCacheTransport(next_transport=next_transport, storage=storage, policy=policy)

        async with AsyncClient(transport=transport) as client:
            with respx.mock:
                # Two different paths
                route1 = respx.get("http://backend1.example.com/api/users").mock(
                    return_value=Response(200, json={"users": []}, headers={"Cache-Control": "public, max-age=3600"})
                )

                route2 = respx.get("http://backend2.example.com/api/posts").mock(
                    return_value=Response(200, json={"posts": []}, headers={"Cache-Control": "public, max-age=3600"})
                )

                # Request different paths
                response1 = await client.get("http://backend1.example.com/api/users")
                assert response1.json() == {"users": []}
                assert route1.called

                response2 = await client.get("http://backend2.example.com/api/posts")
                assert response2.json() == {"posts": []}
                assert route2.called  # Should hit backend because path is different

    async def test_cache_hit_with_query_params(self, mock_storage):
        """Verify cache hit with query parameters across backends."""
        storage = mock_storage
        policy = SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET"], allow_stale=False)
        )

        next_transport = AsyncHTTPTransport()
        transport = AsyncCacheTransport(next_transport=next_transport, storage=storage, policy=policy)

        async with AsyncClient(transport=transport) as client:
            with respx.mock:
                # Same query params, different backends
                route1 = respx.get("http://backend1.example.com/api/search", params={"q": "test", "page": "1"}).mock(
                    return_value=Response(
                        200, json={"results": ["item1"]}, headers={"Cache-Control": "public, max-age=3600"}
                    )
                )

                route2 = respx.get("http://backend2.example.com/api/search", params={"q": "test", "page": "1"}).mock(
                    return_value=Response(
                        200, json={"results": ["item2"]}, headers={"Cache-Control": "public, max-age=3600"}
                    )
                )

                # First request
                response1 = await client.get(
                    "http://backend1.example.com/api/search", params={"q": "test", "page": "1"}
                )
                assert response1.json() == {"results": ["item1"]}
                assert route1.called

                # Second request to different backend, same params (should use cache)
                response2 = await client.get(
                    "http://backend2.example.com/api/search", params={"q": "test", "page": "1"}
                )
                assert response2.json() == {"results": ["item1"]}  # From cache
                assert not route2.called

    async def test_cache_headers_preserved(self, mock_storage):
        """Verify cache-related headers are properly set."""
        storage = mock_storage
        policy = SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET"], allow_stale=False)
        )

        next_transport = AsyncHTTPTransport()
        transport = AsyncCacheTransport(next_transport=next_transport, storage=storage, policy=policy)

        async with AsyncClient(transport=transport) as client:
            with respx.mock:
                route = respx.get("http://backend1.example.com/api/cacheable").mock(
                    return_value=Response(
                        200, content=b"cacheable content", headers={"Cache-Control": "public, max-age=3600"}
                    )
                )

                # First request (cache miss)
                response1 = await client.get("http://backend1.example.com/api/cacheable")
                # Note: X-Cache headers are added by the proxy adapter, not the transport
                # We're testing the transport layer here
                assert response1.status_code == 200
                assert route.call_count == 1

                # Second request to different backend (cache hit)
                response2 = await client.get("http://backend2.example.com/api/cacheable")
                assert response2.status_code == 200
                assert route.call_count == 1  # Still 1, not incremented

                # Content should be the same
                assert response2.content == b"cacheable content"
