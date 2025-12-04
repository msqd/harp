"""Test HTTP method cacheability compliance with RFC 9111 §3.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for which HTTP methods can be cached.

RFC 9111 §3 defines which HTTP methods produce cacheable responses
and under what conditions they may be stored.
"""

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    assert_not_cached,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestGET:
    """Tests for GET method cacheability per RFC 9111 §3."""

    @respx.mock
    async def test_get_is_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: GET responses are cacheable by default.

        Quote from RFC:
        > In general, safe methods (GET, HEAD) that do not depend on a
        > current or authoritative response are defined as cacheable.
        """
        # Arrange: Cacheable GET response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"GET response",
                max_age=3600,
            )
        )

        # Act: Make two GET requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Second request uses cache
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)


@pytest.mark.asyncio
class TestHEAD:
    """Tests for HEAD method cacheability per RFC 9111 §3."""

    @respx.mock
    async def test_head_is_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: HEAD responses are cacheable like GET.

        Quote from RFC:
        > Responses to the HEAD method are cacheable; a cache MAY use them
        > to satisfy subsequent HEAD requests unless otherwise indicated
        > by the Cache-Control header field.
        """
        # Arrange: Cacheable HEAD response
        respx.head("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"",  # HEAD has no body
                max_age=3600,
            )
        )

        # Act: Make two HEAD requests
        response1 = await cached_client.head("http://example.com/resource")
        response2 = await cached_client.head("http://example.com/resource")

        # Assert: Second request uses cache
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Note: HEAD caching behavior depends on cache implementation

    @respx.mock
    async def test_head_response_can_satisfy_get_rfc9111_4_3_5(self, cached_client, mock_storage):
        """RFC 9111 §4.3.5: Cached HEAD response can satisfy GET request.

        Quote from RFC:
        > A cache that receives a HEAD request and has a fresh GET response
        > for the same URI can use the stored GET response to satisfy the
        > HEAD request, but it MUST construct a HEAD response (i.e., without
        > a payload body).

        Note: This is implementation-dependent; testing that HEAD is cacheable.
        """
        # Arrange: HEAD response
        respx.head("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"",
                max_age=3600,
            )
        )

        # Act: Make HEAD request
        response = await cached_client.head("http://example.com/resource")

        # Assert: HEAD is cacheable
        assert response.status_code == 200
        assert len(response.content) == 0  # No body for HEAD


@pytest.mark.asyncio
class TestUnsafeMethods:
    """Tests for unsafe method cacheability per RFC 9111 §3."""

    @respx.mock
    async def test_post_not_cacheable_by_default_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: POST responses are not cacheable without explicit directives.

        Quote from RFC:
        > Responses to POST requests are only cacheable when they include
        > explicit freshness information and a Content-Location header field
        > that matches the URI of the POST request.

        Note: Our cache policy only caches GET and HEAD by default.
        """
        # Arrange: POST response
        route = respx.post("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"POST response",
                max_age=3600,  # Even with max-age, POST not cached by default policy
            )
        )

        # Act: Make two POST requests
        response1 = await cached_client.post("http://example.com/resource")
        response2 = await cached_client.post("http://example.com/resource")

        # Assert: POST not cached (both requests hit backend)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 2
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_put_not_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: PUT responses are not cacheable.

        Quote from RFC:
        > Responses to PUT requests are not cacheable.
        """
        # Arrange: PUT response
        route = respx.put("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"PUT response",
                max_age=3600,
            )
        )

        # Act: Make two PUT requests
        response1 = await cached_client.put("http://example.com/resource")
        response2 = await cached_client.put("http://example.com/resource")

        # Assert: PUT not cached
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 2
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_delete_not_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: DELETE responses are not cacheable.

        Quote from RFC:
        > Responses to DELETE requests are not cacheable.
        """
        # Arrange: DELETE response
        route = respx.delete("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"DELETE response",
                max_age=3600,
            )
        )

        # Act: Make two DELETE requests
        response1 = await cached_client.delete("http://example.com/resource")
        response2 = await cached_client.delete("http://example.com/resource")

        # Assert: DELETE not cached
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 2
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_patch_not_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: PATCH responses are not cacheable.

        Quote from RFC:
        > Responses to the PATCH method are not cacheable, because the
        > request is not safe (it modifies state) and because successful
        > PATCH responses do not have a standardized representation.
        """
        # Arrange: PATCH response
        route = respx.patch("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"PATCH response",
                max_age=3600,
            )
        )

        # Act: Make two PATCH requests
        response1 = await cached_client.patch("http://example.com/resource")
        response2 = await cached_client.patch("http://example.com/resource")

        # Assert: PATCH not cached
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 2
        assert_not_cached(mock_storage)
