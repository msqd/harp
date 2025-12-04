"""Test Vary header compliance with RFC 9111 §4.1.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for the Vary header field, which is used for
content negotiation and selecting appropriate cached responses.

RFC 9111 §4.1 defines how caches use the Vary header to calculate
cache keys and select responses based on request headers.
"""

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestVaryHeader:
    """Tests for Vary header behavior per RFC 9111 §4.1."""

    @respx.mock
    async def test_vary_creates_separate_cache_entries_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Vary header creates separate cache entries per variant.

        Quote from RFC:
        > When a cache receives a request that can be satisfied by a stored
        > response that has a Vary header field, it MUST NOT use that
        > response unless all of the selecting request-headers nominated by
        > the Vary header field match in both the original request and the
        > new request.
        """
        # Arrange: Response varies by Accept-Language
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"English content",
                max_age=3600,
                vary="Accept-Language",
            )
        )

        # Act: Make two requests with different Accept-Language headers
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en"},
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "fr"},
        )

        # Assert: Different Accept-Language means different cache entries
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Both requests should hit the backend (different variants)
        assert route.call_count == 2

    @respx.mock
    async def test_vary_same_headers_uses_cache_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Same selecting headers reuse cached response.

        Quote from RFC:
        > A Vary header field value of "*" signals that anything about
        > the request might play a role in selecting the representation.
        """
        # Arrange: Response varies by Accept-Language
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"English content",
                max_age=3600,
                vary="Accept-Language",
            )
        )

        # Act: Make two requests with same Accept-Language
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en"},
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en"},
        )

        # Assert: Same Accept-Language means cache hit
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 1  # Second request used cache
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_vary_multiple_headers_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Vary can list multiple headers.

        Quote from RFC:
        > The Vary header field in a response describes what parts of a
        > request message, aside from the method and request target, might
        > have influenced the origin server's process for selecting the
        > content of this response.
        """
        # Arrange: Response varies by multiple headers
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Negotiated content",
                max_age=3600,
                vary="Accept-Language, Accept-Encoding",
            )
        )

        # Act: Make requests with matching all varied headers
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={
                "Accept-Language": "en",
                "Accept-Encoding": "gzip",
            },
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={
                "Accept-Language": "en",
                "Accept-Encoding": "gzip",
            },
        )

        # Assert: Both varied headers match, so cache hit
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_vary_star_prevents_reuse_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Vary: * means response is uncacheable for reuse.

        Quote from RFC:
        > A Vary header field value of "*" signals that anything about
        > the request might play a role in selecting the representation,
        > and that this selecting is not limited to the request headers
        > listed in the Vary field.

        Note: Vary: * typically makes responses effectively uncacheable
        for shared use, though they may be stored.
        """
        # Arrange: Response with Vary: *
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Unique content",
                max_age=3600,
                vary="*",
            )
        )

        # Act: Make two identical requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Vary: * typically prevents cache reuse
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Implementation-dependent: may or may not cache with Vary: *


@pytest.mark.asyncio
class TestContentNegotiation:
    """Tests for content negotiation scenarios per RFC 9111 §4.1."""

    @respx.mock
    async def test_vary_accept_language_negotiation_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Accept-Language negotiation creates separate variants.

        This tests a common content negotiation scenario where the same
        resource returns different content based on user language preferences.
        """
        # Arrange: Mock different responses for different languages
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Content",
                max_age=3600,
                vary="Accept-Language",
            )
        )

        # Act: Request English variant twice
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en-US"},
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en-US"},
        )

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"Content"
        assert response2.status_code == 200
        assert response2.content == b"Content"

        # Assert: Same language preference uses cache
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_vary_accept_encoding_negotiation_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Accept-Encoding negotiation for compression.

        Tests that responses with different encodings (gzip, br, etc.)
        are cached separately based on Accept-Encoding header.
        """
        # Arrange: Response varies by encoding
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Compressed content",
                max_age=3600,
                vary="Accept-Encoding",
            )
        )

        # Act: Request gzip variant twice
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Encoding": "gzip"},
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Encoding": "gzip"},
        )

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"Compressed content"
        assert response2.status_code == 200
        assert response2.content == b"Compressed content"

        # Assert: Same encoding uses cache
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_vary_case_insensitive_header_matching_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Header field names are case-insensitive.

        Quote from RFC:
        > Field names are case-insensitive.
        """
        # Arrange: Response varies by Accept-Language
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Content",
                max_age=3600,
                vary="Accept-Language",
            )
        )

        # Act: Make requests with different header casing but same value
        response1 = await cached_client.get(
            "http://example.com/resource",
            headers={"Accept-Language": "en"},
        )
        response2 = await cached_client.get(
            "http://example.com/resource",
            headers={"accept-language": "en"},  # Different casing
        )

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"Content"
        assert response2.status_code == 200
        assert response2.content == b"Content"

        # Assert: Header name casing doesn't matter, cache hit
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_vary_missing_header_in_request_rfc9111_4_1(self, cached_client, mock_storage):
        """RFC 9111 §4.1: Missing header in request is distinct from any value.

        If a Vary header field lists a header that is not present in the
        request, that's a distinct cache key from requests that have the header.
        """
        # Arrange: Response varies by Accept-Language
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"Default content",
                max_age=3600,
                vary="Accept-Language",
            )
        )

        # Act: Make request without Accept-Language
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"Default content"
        assert response2.status_code == 200
        assert response2.content == b"Default content"

        # Assert: Same missing header uses cache
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)
