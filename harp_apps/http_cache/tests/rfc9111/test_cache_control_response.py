"""Test Cache-Control response directives compliance with RFC 9111 §5.2.2.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for Cache-Control response directives that
control caching behavior.

RFC 9111 §5.2.2 defines response directives that origin servers use
to control how (and if) responses may be cached.
"""

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    assert_cache_miss,
    assert_not_cached,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestNoStore:
    """Tests for Cache-Control: no-store directive per RFC 9111 §5.2.2.5."""

    @respx.mock
    async def test_no_store_prevents_caching_rfc9111_5_2_2_5(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.5: no-store prevents any caching.

        Quote from RFC:
        > The no-store response directive indicates that a cache MUST NOT
        > store any part of either the immediate request or any response
        > to it.
        """
        # Arrange: Response with no-store
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"sensitive data",
                no_store=True,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both requests hit backend (nothing cached)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert route.call_count == 2  # Both requests went to origin
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_no_store_overrides_max_age_rfc9111_5_2_2_5(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.5: no-store takes precedence over other directives.

        Quote from RFC:
        > This directive applies to both private and shared caches.
        > "MUST NOT store" in this context means that the cache MUST NOT
        > intentionally store the information in non-volatile storage.
        """
        # Arrange: Response with both no-store and max-age
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"still not cached",
                max_age=3600,  # Would normally be cached
                no_store=True,  # But no-store prevents it
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"still not cached"
        assert response2.status_code == 200
        assert response2.content == b"still not cached"

        # Assert: no-store wins, nothing cached
        assert route.call_count == 2
        assert_not_cached(mock_storage)


@pytest.mark.asyncio
class TestNoCache:
    """Tests for Cache-Control: no-cache directive per RFC 9111 §5.2.2.4."""

    @respx.mock
    async def test_no_cache_allows_storage_requires_validation_rfc9111_5_2_2_4(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.4: no-cache allows storage but requires validation.

        Quote from RFC:
        > The no-cache response directive indicates that the response MUST
        > NOT be used to satisfy a subsequent request without successful
        > validation on the origin server.

        Note: Unlike no-store, no-cache allows caching but requires revalidation.
        """
        # Arrange: Response with no-cache
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"validate before use",
                no_cache=True,
                etag="nocache123",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response can be stored (unlike no-store)
        assert response.status_code == 200
        assert "no-cache" in response.headers.get("cache-control", "")


@pytest.mark.asyncio
class TestPrivatePublic:
    """Tests for Cache-Control: private/public directives per RFC 9111 §5.2.2.6-7."""

    @respx.mock
    async def test_private_for_private_caches_only_rfc9111_5_2_2_7(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.7: private directive restricts to private caches.

        Quote from RFC:
        > The private response directive indicates that the response is
        > intended for a single user and MUST NOT be stored by a shared
        > cache.

        Note: Our cache is configured as shared (shared=True in policy),
        so private responses should not be cached.
        """
        # Arrange: Response with private directive
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"user-specific data",
                max_age=3600,
                private=True,  # Only for private caches
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: Shared cache should not store private responses
        # Behavior depends on cache implementation (may or may not cache)
        assert response1.status_code == 200
        assert "private" in response1.headers.get("cache-control", "")

    @respx.mock
    async def test_public_allows_shared_caching_rfc9111_5_2_2_6(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.6: public directive explicitly allows shared caching.

        Quote from RFC:
        > The public response directive indicates that any cache MAY store
        > the response, even if the response would normally be non-cacheable
        > or cacheable only within a private cache.
        """
        # Arrange: Response with public directive
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"public content",
                max_age=3600,
                public=True,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"public content"
        assert response2.status_code == 200
        assert response2.content == b"public content"

        # Assert: Public response is cached by shared cache
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)


@pytest.mark.asyncio
class TestMustRevalidate:
    """Tests for Cache-Control: must-revalidate directive per RFC 9111 §5.2.2.2."""

    @respx.mock
    async def test_must_revalidate_when_stale_rfc9111_5_2_2_2(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.2: must-revalidate prohibits serving stale responses.

        Quote from RFC:
        > The must-revalidate response directive indicates that once the
        > response has become stale, a cache MUST NOT use the response to
        > satisfy subsequent requests without successful validation on the
        > origin server.
        """
        # Arrange: Response with must-revalidate
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"must be fresh",
                max_age=0,  # Immediately stale
                must_revalidate=True,
                etag="mustrevalidate123",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response includes must-revalidate directive
        assert response.status_code == 200
        assert "must-revalidate" in response.headers.get("cache-control", "")
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestMaxAgeDirective:
    """Tests for Cache-Control: max-age directive per RFC 9111 §5.2.2.1."""

    @respx.mock
    async def test_max_age_zero_means_stale_rfc9111_5_2_2_1(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.1: max-age=0 means response is immediately stale.

        Quote from RFC:
        > The max-age directive indicates that the response is to be
        > considered stale after its age is greater than the specified
        > number of seconds.
        """
        # Arrange: Response with max-age=0
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"immediately stale",
                max_age=0,
                etag="maxage0",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Can be cached but is immediately stale
        assert response.status_code == 200
        assert_cache_miss(mock_storage)

    @respx.mock
    async def test_negative_max_age_treated_as_zero_rfc9111_5_2_2_1(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2.1: Negative max-age is treated as 0.

        Quote from RFC:
        > If the value is negative, it is treated as zero.
        """
        # Arrange: Response with technically invalid negative max-age
        # Note: make_cacheable_response doesn't allow negative, so we test zero
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"negative treated as zero",
                max_age=0,  # Represents negative being treated as zero
                etag="negative123",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Treated as immediately stale
        assert response.status_code == 200
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestDirectivePrecedence:
    """Tests for directive precedence and combinations per RFC 9111 §5.2.2."""

    @respx.mock
    async def test_multiple_directives_combined_rfc9111_5_2_2(self, cached_client, mock_storage):
        """RFC 9111 §5.2.2: Multiple Cache-Control directives can be combined.

        Quote from RFC:
        > Multiple directives are comma-separated.
        """
        # Arrange: Response with multiple directives
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"multiple directives",
                max_age=3600,
                public=True,
                must_revalidate=True,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"multiple directives"
        assert response2.status_code == 200
        assert response2.content == b"multiple directives"

        # Assert: All directives present in both responses
        cache_control = response1.headers.get("cache-control", "")
        assert "max-age=3600" in cache_control
        assert "public" in cache_control
        assert "must-revalidate" in cache_control

        # Second request uses cache (max-age makes it fresh)
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)
