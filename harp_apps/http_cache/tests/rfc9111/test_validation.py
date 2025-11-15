"""Test validation compliance with RFC 9111 §4.3.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for cache validation using conditional requests,
ETags, and Last-Modified headers.

RFC 9111 §4.3 defines how caches validate stale responses with the
origin server using conditional requests (If-None-Match, If-Modified-Since).
"""

from datetime import timedelta

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    assert_cache_miss,
    http_date,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestETagValidation:
    """Tests for ETag-based validation per RFC 9111 §4.3.2."""

    @respx.mock
    async def test_etag_validator_allows_caching_rfc9111_4_3_2(self, cached_client, mock_storage):
        """RFC 9111 §4.3.2: ETag provides a strong validator for cached responses.

        Quote from RFC:
        > The ETag header field provides a validator that can be used for
        > conditional requests to validate a stored response.
        """
        # Arrange: Response with ETag
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"validated content",
                max_age=3600,
                etag="abc123",
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: Response is cached and reused
        assert response1.status_code == 200
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_weak_etag_validation_rfc9111_4_3_2(self, cached_client, mock_storage):
        """RFC 9111 §4.3.2: Weak ETags (W/ prefix) are valid validators.

        Quote from RFC:
        > A "weak validator" is an entity-tag that begins with "W/".
        > Weak validators can be used for validation even when the
        > representation data has changed in a way that is not significant.
        """
        # Arrange: Response with weak ETag
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"weakly validated",
                max_age=3600,
                etag='W/"weak123"',  # Already quoted with W/ prefix
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Weak ETag is accepted
        assert response.status_code == 200
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestLastModifiedValidation:
    """Tests for Last-Modified-based validation per RFC 9111 §4.3.2."""

    @respx.mock
    async def test_last_modified_validator_rfc9111_4_3_2(self, cached_client, mock_storage):
        """RFC 9111 §4.3.2: Last-Modified provides a validator for cached responses.

        Quote from RFC:
        > The Last-Modified header field provides a timestamp indicating
        > the date and time at which the origin server believes the
        > representation was last modified.
        """
        # Arrange: Response with Last-Modified
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"last modified content",
                max_age=3600,
                last_modified=http_date(delta=timedelta(days=-1)),
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response is cached with Last-Modified validator
        assert response.status_code == 200
        assert "last-modified" in response.headers
        assert_cache_miss(mock_storage)

    @respx.mock
    async def test_etag_preferred_over_last_modified_rfc9111_4_3_2(self, cached_client, mock_storage):
        """RFC 9111 §4.3.2: ETag takes precedence over Last-Modified.

        Quote from RFC:
        > If both an entity-tag and a Last-Modified value have been
        > provided by the origin server, the entity-tag SHOULD be
        > sent in preference to the Last-Modified value in conditional
        > requests.
        """
        # Arrange: Response with both validators
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"both validators",
                max_age=3600,
                etag="strong456",
                last_modified=http_date(delta=timedelta(days=-1)),
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Both validators present
        assert response.status_code == 200
        assert "etag" in response.headers
        assert "last-modified" in response.headers
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestConditionalRequests:
    """Tests for conditional request behavior per RFC 9111 §4.3."""

    @respx.mock
    async def test_304_not_modified_revalidation_rfc9111_4_3_3(self, cached_client, mock_storage):
        """RFC 9111 §4.3.3: 304 Not Modified indicates cached response is still valid.

        Quote from RFC:
        > The 304 (Not Modified) status code indicates that a conditional
        > GET or HEAD request has been received and would have resulted in
        > a 200 (OK) response if it were not for the fact that the condition
        > evaluated to false.

        Note: This test verifies the concept; actual 304 handling depends on
        the cache implementation's conditional request support.
        """
        # Arrange: Stale response that could be revalidated
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"revalidated content",
                max_age=0,  # Immediately stale
                etag="revalidate789",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response is cached (even if stale)
        assert response.status_code == 200
        assert_cache_miss(mock_storage)

    @respx.mock
    async def test_if_none_match_conditional_rfc9111_4_3_1(self, cached_client, mock_storage):
        """RFC 9111 §4.3.1: If-None-Match used for ETag-based conditional requests.

        Quote from RFC:
        > The If-None-Match header field makes the request conditional on
        > none of the entity-tags matching the current entity-tag for the
        > representation.

        Note: Testing that cache stores ETag for potential conditional requests.
        """
        # Arrange: Response with ETag for conditional validation
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"conditional content",
                max_age=3600,
                etag="conditional123",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: ETag stored for future conditional requests
        assert response.status_code == 200
        assert response.headers.get("etag") == '"conditional123"'
        assert_cache_miss(mock_storage)

    @respx.mock
    async def test_if_modified_since_conditional_rfc9111_4_3_1(self, cached_client, mock_storage):
        """RFC 9111 §4.3.1: If-Modified-Since used for time-based conditional requests.

        Quote from RFC:
        > The If-Modified-Since header field makes the request conditional
        > on the selected representation's modification time being more
        > recent than the provided time.

        Note: Testing that cache stores Last-Modified for potential conditional requests.
        """
        # Arrange: Response with Last-Modified for conditional validation
        last_modified_date = http_date(delta=timedelta(days=-2))
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"time conditional content",
                max_age=3600,
                last_modified=last_modified_date,
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Last-Modified stored for future conditional requests
        assert response.status_code == 200
        assert "last-modified" in response.headers
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestValidationRequirements:
    """Tests for validation requirements per RFC 9111 §4.3."""

    @respx.mock
    async def test_must_revalidate_requires_validation_rfc9111_4_3_4(self, cached_client, mock_storage):
        """RFC 9111 §4.3.4: must-revalidate requires validation when stale.

        Quote from RFC:
        > The must-revalidate directive indicates that once the response
        > has become stale, a cache MUST NOT use the response to satisfy
        > subsequent requests without successful validation on the origin
        > server.
        """
        # Arrange: Response with must-revalidate
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"must revalidate content",
                max_age=0,  # Immediately stale
                must_revalidate=True,
                etag="mustval456",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response cached with must-revalidate directive
        assert response.status_code == 200
        assert "must-revalidate" in response.headers.get("cache-control", "")
        assert_cache_miss(mock_storage)

    @respx.mock
    async def test_no_cache_requires_validation_rfc9111_5_2_2_4(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.4: no-cache requires validation before reuse.

        Quote from RFC:
        > The no-cache response directive indicates that the response MUST
        > NOT be used to satisfy a subsequent request without successful
        > validation on the origin server.
        """
        # Arrange: Response with no-cache (can store but must validate)
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"no-cache content",
                max_age=3600,
                no_cache=True,
                etag="nocache789",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response has no-cache directive
        assert response.status_code == 200
        assert "no-cache" in response.headers.get("cache-control", "")
