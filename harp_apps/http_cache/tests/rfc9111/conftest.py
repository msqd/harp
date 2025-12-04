"""Shared fixtures and helpers for RFC 9111 compliance tests.

RFC 9111 Reference: https://www.rfc-editor.org/rfc/rfc9111.html

This module provides reusable test infrastructure for verifying HARP's
HTTP caching implementation complies with RFC 9111 (HTTP Caching).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, Response, AsyncHTTPTransport

from harp_apps.http_cache.transports import AsyncCacheTransport


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def rfc_compliant_policy():
    """Standard RFC 9111-compliant cache policy.

    Returns a SpecificationPolicy configured for shared cache behavior
    following RFC 9111 defaults:
    - Shared cache (not private browser cache)
    - Only GET and HEAD methods are cacheable
    - Stale responses not allowed by default
    """
    return SpecificationPolicy(
        cache_options=CacheOptions(
            shared=True,
            supported_methods=["GET", "HEAD"],
            allow_stale=False,
        )
    )


@pytest.fixture
async def cached_client(mock_storage, rfc_compliant_policy):
    """HTTP client with RFC-compliant caching enabled.

    Uses mock storage to track cache operations and respx for mocking
    backend responses.
    """
    next_transport = AsyncHTTPTransport()
    transport = AsyncCacheTransport(
        next_transport=next_transport,
        storage=mock_storage,
        policy=rfc_compliant_policy,
    )

    async with AsyncClient(transport=transport) as client:
        yield client


# ============================================================================
# RESPONSE BUILDERS
# ============================================================================


def make_cacheable_response(
    status_code: int = 200,
    content: bytes = b"test content",
    max_age: Optional[int] = None,
    s_maxage: Optional[int] = None,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
    expires: Optional[str] = None,
    vary: Optional[str] = None,
    no_cache: bool = False,
    no_store: bool = False,
    private: bool = False,
    public: bool = False,
    must_revalidate: bool = False,
    **extra_headers,
) -> Response:
    """Build an HTTP response with specified cache control headers.

    Args:
        status_code: HTTP status code (default: 200)
        content: Response body content
        max_age: Cache-Control max-age in seconds
        s_maxage: Cache-Control s-maxage in seconds (shared cache)
        etag: ETag header value (without quotes, will be quoted)
        last_modified: Last-Modified header value (HTTP date format)
        expires: Expires header value (HTTP date format)
        vary: Vary header value (e.g., "Accept-Language")
        no_cache: Add Cache-Control: no-cache directive
        no_store: Add Cache-Control: no-store directive
        private: Add Cache-Control: private directive
        public: Add Cache-Control: public directive
        must_revalidate: Add Cache-Control: must-revalidate directive
        **extra_headers: Additional headers to include

    Returns:
        Response object with configured headers

    Example:
        >>> make_cacheable_response(max_age=3600, etag="abc123")
        Response with Cache-Control: max-age=3600 and ETag: "abc123"
    """
    headers = {"content-type": "text/plain"}

    # Build Cache-Control header
    cache_control_parts = []
    if max_age is not None:
        cache_control_parts.append(f"max-age={max_age}")
    if s_maxage is not None:
        cache_control_parts.append(f"s-maxage={s_maxage}")
    if no_cache:
        cache_control_parts.append("no-cache")
    if no_store:
        cache_control_parts.append("no-store")
    if private:
        cache_control_parts.append("private")
    if public:
        cache_control_parts.append("public")
    if must_revalidate:
        cache_control_parts.append("must-revalidate")

    if cache_control_parts:
        headers["cache-control"] = ", ".join(cache_control_parts)

    # Add validation headers
    if etag is not None:
        # Quote ETag if not already quoted
        if not (etag.startswith('"') and etag.endswith('"')):
            etag = f'"{etag}"'
        headers["etag"] = etag

    if last_modified is not None:
        headers["last-modified"] = last_modified

    if expires is not None:
        headers["expires"] = expires

    if vary is not None:
        headers["vary"] = vary

    # Add any extra headers
    headers.update(extra_headers)

    return Response(status_code=status_code, content=content, headers=headers)


def http_date(dt: Optional[datetime] = None, delta: Optional[timedelta] = None) -> str:
    """Format datetime as HTTP date string (RFC 9110 §5.6.7).

    Args:
        dt: Datetime to format (default: current UTC time)
        delta: Timedelta to add/subtract from dt

    Returns:
        HTTP date string (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

    Example:
        >>> http_date(delta=timedelta(hours=1))  # 1 hour from now
        'Wed, 15 Nov 2025 14:09:33 GMT'
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    if delta is not None:
        dt = dt + delta

    # HTTP date format: Day, DD Mon YYYY HH:MM:SS GMT
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


# ============================================================================
# ASSERTION HELPERS
# ============================================================================


def assert_cache_hit(storage, expected_key_count: int = 1):
    """Assert that cache was used (no new storage entries created).

    Args:
        storage: MockAsyncStorage instance
        expected_key_count: Expected number of total cache keys created

    Raises:
        AssertionError: If more cache keys were created than expected
    """
    assert len(storage.created_keys) == expected_key_count, (
        f"Expected {expected_key_count} cache key(s), got {len(storage.created_keys)}"
    )


def assert_cache_miss(storage):
    """Assert that cache was not used (new entry was created).

    Args:
        storage: MockAsyncStorage instance

    Raises:
        AssertionError: If no cache entries were created
    """
    assert len(storage.created_keys) > 0, "Expected cache entry to be created"


def assert_not_cached(storage):
    """Assert that nothing was stored in cache.

    Args:
        storage: MockAsyncStorage instance

    Raises:
        AssertionError: If any cache entries were created
    """
    assert len(storage.created_keys) == 0, f"Expected no caching, but {len(storage.created_keys)} entries created"


def assert_response_fresh(response: Response):
    """Assert response is fresh per RFC 9111 §4.2.

    A response is fresh if its age has not yet exceeded its freshness lifetime.

    Args:
        response: Response to check

    Raises:
        AssertionError: If response is stale
    """
    # Check for Warning header (110 = "Response is Stale")
    warning = response.headers.get("warning", "")
    assert "110" not in warning, "Response has stale warning (110)"

    # If Age header present, verify it's less than max-age
    if "age" in response.headers and "cache-control" in response.headers:
        age = int(response.headers["age"])
        cache_control = response.headers["cache-control"]

        # Extract max-age
        for directive in cache_control.split(","):
            directive = directive.strip()
            if directive.startswith("max-age="):
                max_age = int(directive.split("=")[1])
                assert age < max_age, f"Response is stale: age={age} >= max-age={max_age}"
                break


def assert_response_stale(response: Response):
    """Assert response is stale per RFC 9111 §4.2.

    Args:
        response: Response to check

    Raises:
        AssertionError: If response is fresh
    """
    # Check for Age and max-age
    if "age" in response.headers and "cache-control" in response.headers:
        age = int(response.headers["age"])
        cache_control = response.headers["cache-control"]

        # Extract max-age
        for directive in cache_control.split(","):
            directive = directive.strip()
            if directive.startswith("max-age="):
                max_age = int(directive.split("=")[1])
                assert age >= max_age, f"Response is fresh: age={age} < max-age={max_age}"
                return

    # Otherwise check for stale warning
    warning = response.headers.get("warning", "")
    assert "110" in warning, "Response should have stale warning (110)"


# ============================================================================
# RFC SECTION MAPPING (for documentation)
# ============================================================================


class RFC9111:
    """RFC 9111 section references for test documentation.

    Use these constants in test docstrings to reference specific
    sections of RFC 9111.
    """

    # Major sections
    STORING = "3"  # Storing Responses in Caches
    CONSTRUCTING = "4"  # Constructing Responses from Caches
    HEADERS = "5"  # Header Field Definitions
    INVALIDATION = "7"  # Invalidating Stored Responses

    # Subsections - Constructing Responses
    VARY = "4.1"  # Calculating Cache Keys with the Vary Header Field
    FRESHNESS = "4.2"  # Freshness
    VALIDATION = "4.3"  # Validation

    # Subsections - Headers
    AGE = "5.1"  # Age
    CACHE_CONTROL = "5.2"  # Cache-Control
    CACHE_CONTROL_REQUEST = "5.2.1"  # Request Directives
    CACHE_CONTROL_RESPONSE = "5.2.2"  # Response Directives
    EXPIRES = "5.3"  # Expires
    PRAGMA = "5.4"  # Pragma
