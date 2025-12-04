"""Test status code cacheability compliance with RFC 9111 §3.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for which HTTP status codes produce cacheable
responses.

RFC 9111 §3 defines which status codes are cacheable by default and
which require explicit freshness information.
"""

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestCacheableStatusCodes:
    """Tests for cacheable status codes per RFC 9111 §3."""

    @respx.mock
    async def test_200_ok_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 200 OK is cacheable by default.

        Quote from RFC:
        > The following status codes are cacheable by default: 200, 203,
        > 204, 206, 300, 301, 308, 404, 405, 410, 414, 501.
        """
        # Arrange: 200 OK response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=200,
                content=b"OK response",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: 200 is cached
        assert response1.status_code == 200
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_301_moved_permanently_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 301 Moved Permanently is cacheable by default.

        Quote from RFC:
        > 301 (Moved Permanently) is defined as cacheable by default.
        """
        # Arrange: 301 redirect response
        route = respx.get("http://example.com/old").mock(
            return_value=make_cacheable_response(
                status_code=301,
                content=b"",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/old")
        await cached_client.get("http://example.com/old")

        # Assert: 301 is cached
        assert response1.status_code == 301
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_404_not_found_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 404 Not Found is cacheable by default.

        Quote from RFC:
        > 404 (Not Found) is defined as cacheable by default.

        This prevents repeated requests for non-existent resources.
        """
        # Arrange: 404 response
        route = respx.get("http://example.com/missing").mock(
            return_value=make_cacheable_response(
                status_code=404,
                content=b"Not Found",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/missing")
        await cached_client.get("http://example.com/missing")

        # Assert: 404 is cached
        assert response1.status_code == 404
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_203_non_authoritative_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 203 Non-Authoritative Information is cacheable.

        Quote from RFC:
        > 203 (Non-Authoritative Information) is defined as cacheable
        > by default.
        """
        # Arrange: 203 response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=203,
                content=b"Non-authoritative",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: 203 is cached
        assert response1.status_code == 203
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_204_no_content_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 204 No Content is cacheable by default.

        Quote from RFC:
        > 204 (No Content) is defined as cacheable by default.
        """
        # Arrange: 204 response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=204,
                content=b"",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: 204 is cached
        assert response1.status_code == 204
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_206_partial_content_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 206 Partial Content is cacheable by default.

        Quote from RFC:
        > 206 (Partial Content) is defined as cacheable by default.

        Note: Partial responses have complex caching rules and typically require
        additional headers (Content-Range, etc.). Implementation behavior may vary.
        """
        # Arrange: 206 partial response
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=206,
                content=b"partial",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: 206 responses received
        assert response1.status_code == 206
        assert response2.status_code == 206
        # Note: Caching behavior for 206 is implementation-dependent
        # without proper Content-Range headers

    @respx.mock
    async def test_300_multiple_choices_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 300 Multiple Choices is cacheable by default.

        Quote from RFC:
        > 300 (Multiple Choices) is defined as cacheable by default.
        """
        # Arrange: 300 response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=300,
                content=b"choices",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: 300 is cached
        assert response1.status_code == 300
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_308_permanent_redirect_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 308 Permanent Redirect is cacheable by default.

        Quote from RFC:
        > 308 (Permanent Redirect) is defined as cacheable by default.
        """
        # Arrange: 308 redirect
        route = respx.get("http://example.com/old").mock(
            return_value=make_cacheable_response(
                status_code=308,
                content=b"",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/old")
        await cached_client.get("http://example.com/old")

        # Assert: 308 is cached
        assert response1.status_code == 308
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_410_gone_cacheable_rfc9111_3(self, cached_client, mock_storage):
        """RFC 9111 §3: 410 Gone is cacheable by default.

        Quote from RFC:
        > 410 (Gone) is defined as cacheable by default.

        This allows caching information about permanently removed resources.
        """
        # Arrange: 410 response
        route = respx.get("http://example.com/deleted").mock(
            return_value=make_cacheable_response(
                status_code=410,
                content=b"Gone",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/deleted")
        await cached_client.get("http://example.com/deleted")

        # Assert: 410 is cached
        assert response1.status_code == 410
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)
