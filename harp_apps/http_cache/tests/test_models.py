"""Unit tests for WrappedRequest class."""

from typing import AsyncIterator

import pytest
from hishel import Headers, Request

from harp_apps.http_cache.models import WrappedRequest


class TestWrappedRequestBasicWrapping:
    """Test basic wrapping behavior without overrides."""

    def test_wraps_request_without_overrides(self):
        """Wrapping without overrides preserves all original attributes."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original)

        assert wrapped.method == original.method
        assert wrapped.url == original.url
        assert wrapped.headers == original.headers

    def test_stores_wrapped_request(self):
        """The wrapped request is accessible via unwrap()."""
        original = Request(method="GET", url="http://backend1.local/api/users")

        wrapped = WrappedRequest(original)

        assert wrapped.unwrap() is original

    def test_inherits_from_request(self):
        """WrappedRequest is a proper Request subclass."""
        original = Request(method="GET", url="http://backend1.local/api/users")
        wrapped = WrappedRequest(original)

        assert isinstance(wrapped, Request)
        assert isinstance(wrapped, WrappedRequest)


class TestWrappedRequestUrlOverride:
    """Test URL override functionality."""

    def test_overrides_url_only(self):
        """Overriding URL changes the wrapped request's URL."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert wrapped.method == original.method
        assert wrapped.headers == original.headers

    def test_url_override_preserves_original(self):
        """URL override doesn't modify the original wrapped request."""
        original = Request(method="GET", url="http://backend1.local/api/users")

        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert original.url == "http://backend1.local/api/users"


class TestWrappedRequestMethodOverride:
    """Test method override functionality."""

    def test_overrides_method_only(self):
        """Overriding method changes the wrapped request's method."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original, method="POST")

        assert wrapped.method == "POST"
        assert wrapped.url == original.url
        assert wrapped.headers == original.headers


class TestWrappedRequestHeadersOverride:
    """Test headers override functionality."""

    def test_overrides_headers_only(self):
        """Overriding headers changes the wrapped request's headers."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        new_headers = Headers({"accept": "text/html", "user-agent": "test"})
        wrapped = WrappedRequest(original, headers=new_headers)

        assert wrapped.headers == new_headers
        assert wrapped.method == original.method
        assert wrapped.url == original.url


class TestWrappedRequestStreamOverride:
    """Test stream override functionality."""

    @pytest.mark.asyncio
    async def test_overrides_stream_only(self):
        """Overriding stream changes the wrapped request's stream."""

        async def original_stream() -> AsyncIterator[bytes]:
            yield b"original data"

        async def new_stream() -> AsyncIterator[bytes]:
            yield b"new data"

        original = Request(method="POST", url="http://backend1.local/api/upload", stream=original_stream())

        wrapped = WrappedRequest(original, stream=new_stream())

        # Consume the streams to verify they're different
        wrapped_data = b"".join([chunk async for chunk in wrapped.stream])
        assert wrapped_data == b"new data"


class TestWrappedRequestMetadataOverride:
    """Test metadata override functionality."""

    def test_overrides_metadata_only(self):
        """Overriding metadata changes the wrapped request's metadata."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            metadata={"original": "metadata"},
        )

        new_metadata = {"new": "metadata", "cache_key": "custom"}
        wrapped = WrappedRequest(original, metadata=new_metadata)

        assert wrapped.metadata == new_metadata
        assert wrapped.method == original.method
        assert wrapped.url == original.url


class TestWrappedRequestMultipleOverrides:
    """Test multiple simultaneous overrides."""

    def test_overrides_multiple_attributes(self):
        """Can override multiple attributes simultaneously."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
            metadata={"original": "metadata"},
        )

        wrapped = WrappedRequest(
            original,
            method="POST",
            url="http://normalized-endpoint/api/users",
            headers=Headers({"content-type": "application/json"}),
            metadata={"new": "metadata"},
        )

        assert wrapped.method == "POST"
        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert wrapped.headers == Headers({"content-type": "application/json"})
        assert wrapped.metadata == {"new": "metadata"}

    def test_overrides_all_attributes(self):
        """Can override all attributes at once."""

        async def new_stream() -> AsyncIterator[bytes]:
            yield b"new data"

        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
            metadata={"original": "metadata"},
        )

        wrapped = WrappedRequest(
            original,
            method="POST",
            url="http://normalized-endpoint/api/users",
            headers=Headers({"content-type": "application/json"}),
            stream=new_stream(),
            metadata={"new": "metadata"},
        )

        assert wrapped.method == "POST"
        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert wrapped.headers == Headers({"content-type": "application/json"})
        assert wrapped.metadata == {"new": "metadata"}


class TestWrappedRequestUnwrap:
    """Test unwrap functionality."""

    def test_unwrap_returns_original_request(self):
        """unwrap() returns the exact original Request instance."""
        original = Request(method="GET", url="http://backend1.local/api/users")

        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        assert wrapped.unwrap() is original

    def test_unwrap_preserves_original_attributes(self):
        """Unwrapped request has all original attributes intact."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
            metadata={"original": "metadata"},
        )

        wrapped = WrappedRequest(
            original,
            method="POST",
            url="http://normalized-endpoint/api/users",
            headers=Headers({"content-type": "text/html"}),
            metadata={"new": "metadata"},
        )

        unwrapped = wrapped.unwrap()

        assert unwrapped.method == "GET"
        assert unwrapped.url == "http://backend1.local/api/users"
        assert unwrapped.headers == Headers({"accept": "application/json"})
        assert unwrapped.metadata == {"original": "metadata"}

    def test_multiple_unwraps_return_same_instance(self):
        """Multiple calls to unwrap() return the same instance."""
        original = Request(method="GET", url="http://backend1.local/api/users")
        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        unwrapped1 = wrapped.unwrap()
        unwrapped2 = wrapped.unwrap()

        assert unwrapped1 is unwrapped2
        assert unwrapped1 is original


class TestWrappedRequestLoadBalancingScenario:
    """Test scenarios specific to load-balanced cache key normalization."""

    def test_different_backends_same_cache_url(self):
        """Different backend URLs can map to same normalized URL."""
        request1 = Request(method="GET", url="http://backend1.local:8001/api/users")
        request2 = Request(method="GET", url="http://backend2.local:8002/api/users")

        normalized_url = "http://normalized-endpoint/api/users"

        wrapped1 = WrappedRequest(request1, url=normalized_url)
        wrapped2 = WrappedRequest(request2, url=normalized_url)

        # Both wrapped requests have the same URL (for cache keys)
        assert wrapped1.url == wrapped2.url
        assert wrapped1.url == normalized_url

        # But unwrapping reveals different original URLs
        assert wrapped1.unwrap().url == "http://backend1.local:8001/api/users"
        assert wrapped2.unwrap().url == "http://backend2.local:8002/api/users"

    def test_preserves_all_request_attributes_for_transmission(self):
        """Original request attributes are preserved for actual transmission."""
        original = Request(
            method="POST",
            url="http://backend1.local:8001/api/users",
            headers=Headers({"content-type": "application/json", "authorization": "Bearer token123"}),
            metadata={"timeout": 30, "endpoint": "backend1"},
        )

        # Normalize URL for cache key
        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        # Wrapped request has normalized URL for cache
        assert wrapped.url == "http://normalized-endpoint/api/users"

        # But unwrapped request retains all original attributes for transmission
        unwrapped = wrapped.unwrap()
        assert unwrapped.method == "POST"
        assert unwrapped.url == "http://backend1.local:8001/api/users"
        assert unwrapped.headers == Headers({"content-type": "application/json", "authorization": "Bearer token123"})
        assert unwrapped.metadata == {"timeout": 30, "endpoint": "backend1"}


class TestWrappedRequestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_wrapping_with_empty_headers(self):
        """Can wrap requests with empty headers."""
        original = Request(method="GET", url="http://backend1.local/api/users", headers=Headers({}))

        wrapped = WrappedRequest(original)

        assert wrapped.headers == Headers({})

    def test_wrapping_with_empty_metadata(self):
        """Can wrap requests with empty metadata."""
        original = Request(method="GET", url="http://backend1.local/api/users", metadata={})

        wrapped = WrappedRequest(original)

        assert wrapped.metadata == {}

    def test_override_with_none_keeps_original(self):
        """Explicitly passing None for overrides keeps original values."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original, method=None, url=None, headers=None, metadata=None)

        assert wrapped.method == original.method
        assert wrapped.url == original.url
        assert wrapped.headers == original.headers
