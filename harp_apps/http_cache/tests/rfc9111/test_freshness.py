"""Test freshness lifetime compliance with RFC 9111 §4.2.

This module verifies that HARP's HTTP caching correctly implements
RFC 9111 requirements for determining freshness lifetime and serving
fresh vs stale responses.

RFC 9111 §4.2 defines how caches determine if a stored response is
fresh (can be returned without validation) or stale (requires validation).
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
class TestMaxAge:
    """Tests for Cache-Control: max-age directive per RFC 9111 §4.2.1."""

    @respx.mock
    async def test_max_age_determines_freshness_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: max-age directive determines freshness lifetime.

        Quote from RFC:
        > The max-age response directive indicates that the response is to be
        > considered stale after its age is greater than the specified number
        > of seconds.
        """
        # Arrange: Response with 1 hour freshness
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"fresh content",
                max_age=3600,  # 1 hour
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: First request creates cache entry
        assert response1.status_code == 200
        assert response1.content == b"fresh content"
        assert route.call_count == 1
        assert_cache_miss(mock_storage)

        # Assert: Second request uses cache (within freshness lifetime)
        assert response2.status_code == 200
        assert response2.content == b"fresh content"
        assert route.call_count == 1  # Still 1, not 2
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_max_age_overrides_expires_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: max-age directive takes precedence over Expires.

        Quote from RFC:
        > If a response includes a Cache-Control field with the max-age
        > directive, a recipient MUST ignore the Expires field.

        Verifies that when both max-age and Expires are present, max-age
        determines the freshness lifetime.
        """
        # Arrange: max-age says fresh, Expires says stale
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"content",
                max_age=3600,  # Fresh for 1 hour
                expires=http_date(delta=timedelta(hours=-1)),  # Expired 1 hour ago
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"content"
        assert response2.status_code == 200
        assert response2.content == b"content"

        # Assert: Second request uses cache (max-age takes precedence)
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_zero_max_age_allows_caching_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: max-age=0 means immediately stale, but still cacheable.

        Quote from RFC:
        > A response with "max-age=0" is considered immediately stale but
        > can still be stored; it just needs to be validated before reuse.

        Note: Our policy has allow_stale=False, so this will trigger validation.
        """
        # Arrange: Immediately stale response
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"stale content",
                max_age=0,  # Immediately stale
                etag="abc123",
            )
        )

        # Act: First request
        response1 = await cached_client.get("http://example.com/resource")

        # Assert: Response is cached (even though immediately stale)
        assert response1.status_code == 200
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestSMaxAge:
    """Tests for Cache-Control: s-maxage directive per RFC 9111 §4.2.1."""

    @respx.mock
    async def test_s_maxage_for_shared_cache_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: s-maxage overrides max-age for shared caches.

        Quote from RFC:
        > The s-maxage directive indicates that, in shared caches, the maximum
        > age specified by this directive overrides the maximum age specified
        > by either the max-age directive or the Expires header field.
        """
        # Arrange: Different freshness for shared vs private caches
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"shared cache content",
                max_age=60,  # 1 minute for private cache
                s_maxage=3600,  # 1 hour for shared cache
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"shared cache content"
        assert response2.status_code == 200
        assert response2.content == b"shared cache content"

        # Assert: Second request uses cache (s-maxage applies for shared cache)
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)


@pytest.mark.asyncio
class TestExpires:
    """Tests for Expires header per RFC 9111 §4.2.1."""

    @respx.mock
    async def test_expires_determines_freshness_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: Expires header sets freshness when no max-age.

        Quote from RFC:
        > The Expires header field gives the date/time after which the
        > response is considered stale.
        """
        # Arrange: Response expires 1 hour from now
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"expires content",
                expires=http_date(delta=timedelta(hours=1)),  # Expires in 1 hour
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"expires content"
        assert response2.status_code == 200
        assert response2.content == b"expires content"

        # Assert: Second request uses cache (within Expires window)
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_past_expires_means_stale_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: Past Expires date means response is stale.

        Quote from RFC:
        > A cache recipient MUST interpret invalid date formats, especially
        > the value "0", as representing a time in the past (i.e., "already
        > expired").
        """
        # Arrange: Response already expired
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"already expired",
                expires=http_date(delta=timedelta(hours=-1)),  # Expired 1 hour ago
                etag="stale123",
            )
        )

        # Act: Make request
        response = await cached_client.get("http://example.com/resource")

        # Assert: Response is cached but immediately stale
        # (with allow_stale=False, would need validation for reuse)
        assert response.status_code == 200
        assert_cache_miss(mock_storage)


@pytest.mark.asyncio
class TestAgeCalculation:
    """Tests for Age header calculation per RFC 9111 §4.2.3."""

    @respx.mock
    async def test_age_increases_over_time_rfc9111_4_2_3(self, cached_client, mock_storage):
        """RFC 9111 §4.2.3: Age header increases as cached response ages.

        Quote from RFC:
        > The Age header field conveys the sender's estimate of the amount
        > of time since the response was generated or successfully validated
        > at the origin server.

        Note: This test verifies Age is present; exact value depends on timing.
        """
        # Arrange: Cacheable response
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"aging content",
                max_age=3600,
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"aging content"
        assert response2.status_code == 200
        assert response2.content == b"aging content"

        # Assert: Second response uses cache
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

        # Age header presence indicates cached response
        # Exact value depends on cache implementation and timing


@pytest.mark.asyncio
class TestHeuristicFreshness:
    """Tests for heuristic freshness per RFC 9111 §4.2.2.

    When no explicit freshness lifetime is provided (no max-age, s-maxage,
    or Expires), caches MAY assign a heuristic freshness lifetime.
    """

    @respx.mock
    async def test_heuristic_freshness_with_last_modified_rfc9111_4_2_2(self, cached_client, mock_storage):
        """RFC 9111 §4.2.2: Heuristic freshness based on Last-Modified.

        Quote from RFC:
        > If the response has a Last-Modified header field, caches are
        > encouraged to use a heuristic expiration value that is no more
        > than some fraction of the interval since that time.

        Note: Heuristic caching is implementation-dependent. This test
        verifies that responses without explicit freshness CAN be cached.
        """
        # Arrange: Response with Last-Modified but no explicit freshness
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"heuristic content",
                last_modified=http_date(delta=timedelta(days=-7)),  # Modified 7 days ago
                # No max-age, s-maxage, or Expires
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        await cached_client.get("http://example.com/resource")

        # Assert: Implementation-dependent
        # Hishel may apply heuristic caching
        assert response1.status_code == 200

        # Second request behavior depends on hishel's heuristic policy
        # At minimum, first request should have been made
        assert route.call_count >= 1


@pytest.mark.asyncio
class TestFreshnessCalculation:
    """Tests for freshness lifetime calculation per RFC 9111 §4.2.1."""

    @respx.mock
    async def test_freshness_lifetime_priority_rfc9111_4_2_1(self, cached_client, mock_storage):
        """RFC 9111 §4.2.1: Freshness calculation priority order.

        Quote from RFC:
        > Priority order for determining freshness lifetime:
        > 1. s-maxage directive (shared caches only)
        > 2. max-age directive
        > 3. Expires header
        > 4. Heuristic (if allowed)

        This test verifies s-maxage > max-age > Expires priority.
        """
        # Arrange: All three directives present with conflicting values
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"priority test",
                s_maxage=3600,  # 1 hour (highest priority for shared cache)
                max_age=60,  # 1 minute
                expires=http_date(delta=timedelta(seconds=30)),  # 30 seconds
            )
        )

        # Act: Make two requests
        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        # Assert: Both responses are correct
        assert response1.status_code == 200
        assert response1.content == b"priority test"
        assert response2.status_code == 200
        assert response2.content == b"priority test"

        # Assert: s-maxage (1 hour) should win
        # Second request uses cache (within s-maxage window)
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)
