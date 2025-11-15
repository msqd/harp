"""Integration tests for normalized cache transport with load balancing."""

import time
import uuid
from typing import Optional, List

import pytest
import respx
from hishel import AsyncBaseStorage, CacheOptions, Entry, EntryMeta, SpecificationPolicy
from httpcore import Request as HttpcoreRequest
from httpcore import Response as HttpcoreResponse
from httpx import AsyncClient, Response, AsyncHTTPTransport

from harp_apps.http_cache.transports import AsyncCacheTransport


class MockAsyncStorage(AsyncBaseStorage):
    """Mock storage implementation for testing."""

    def __init__(self):
        super().__init__()
        self.entries: dict[str, list[Entry]] = {}
        self.contents: dict[str, bytes] = {}  # Store response bodies separately
        self.created_keys: list[str] = []

    async def create_entry(
        self,
        request: HttpcoreRequest,
        response: HttpcoreResponse,
        key: str,
        id_: Optional[object] = None,
    ) -> Entry:
        """Store an entry and track the cache key used."""
        from collections.abc import AsyncIterable, AsyncIterator
        from hishel._utils import make_async_iterator
        from dataclasses import replace

        entry_id = id_ or uuid.uuid4()

        # Read and store the response stream content
        # This mimics what real storage does (serialize/deserialize)
        if isinstance(response.stream, (AsyncIterator, AsyncIterable)):
            content = b"".join([chunk async for chunk in response.stream])
            # Store the content separately by entry ID
            self.contents[str(entry_id)] = content
            # Create a new response with a fresh stream containing the same content
            response = replace(response, stream=make_async_iterator([content]))

        entry = Entry(
            id=entry_id,
            request=request,
            response=response,
            meta=EntryMeta(created_at=time.time(), deleted_at=None),
            cache_key=key.encode("utf-8"),
            extra={"number_of_uses": 0},
        )
        self.entries.setdefault(key, []).append(entry)
        self.created_keys.append(key)
        return entry

    async def get_entries(
        self,
        key: str,
    ) -> List[Entry]:
        """Retrieve entries by key."""
        from hishel._utils import make_async_iterator
        from dataclasses import replace

        entries = self.entries.get(key, [])

        # Recreate streams for each retrieved entry
        # This mimics what real storage does when deserializing
        result = []
        for entry in entries:
            # Get the stored content
            content = self.contents.get(str(entry.id), b"")
            # Create a fresh response with a new stream
            fresh_response = replace(entry.response, stream=make_async_iterator([content]))
            fresh_entry = replace(entry, response=fresh_response)
            result.append(fresh_entry)

        return result

    async def update_entry(
        self,
        entry: Entry,
        request: HttpcoreRequest,
        response: HttpcoreResponse,
    ) -> Entry:
        """Update an existing entry."""
        entry.request = request
        entry.response = response
        return entry

    async def remove_entry(
        self,
        entry: Entry,
    ) -> None:
        """Remove an entry from storage."""
        for key, entries in self.entries.items():
            if entry in entries:
                entries.remove(entry)
                break


@pytest.mark.asyncio
class TestLoadBalancingCacheIntegration:
    """Test cache behavior with load-balanced backends."""

    async def test_cache_hit_across_backends(self):
        """Verify cache hit when switching between load-balanced backends."""
        # Mock storage to track cache operations
        storage = MockAsyncStorage()
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

    async def test_cache_miss_different_paths(self):
        """Verify cache miss when paths differ between backends."""
        storage = MockAsyncStorage()
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

    async def test_cache_hit_with_query_params(self):
        """Verify cache hit with query parameters across backends."""
        storage = MockAsyncStorage()
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

    async def test_cache_headers_preserved(self):
        """Verify cache-related headers are properly set."""
        storage = MockAsyncStorage()
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
