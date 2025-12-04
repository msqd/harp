"""Unit tests for WrappedRequest class.

WrappedRequest is a simple wrapper that allows overriding Request attributes
(primarily URL) for cache key normalization while preserving the original
request for actual transmission.
"""

from dataclasses import replace

from hishel import Headers, Request

from harp_apps.http_cache.models import WrappedRequest


class TestWrappedRequest:
    """Test WrappedRequest wrapper functionality."""

    def test_wraps_request_preserving_all_attributes(self):
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
        assert wrapped.unwrap() is original

    def test_url_override_for_cache_key_normalization(self):
        """URL override allows cache key normalization while preserving original URL."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        # Normalize URL for cache (replace backend-specific URL with endpoint name)
        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        # Wrapped request has normalized URL for cache key generation
        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert wrapped.method == original.method
        assert wrapped.headers == original.headers

        # Original request unchanged - will be used for actual transmission
        assert original.url == "http://backend1.local/api/users"

    def test_unwrap_returns_original_request_intact(self):
        """unwrap() returns the exact original request with all attributes intact."""
        original = Request(
            method="POST",
            url="http://backend1.local/api/users",
            headers=Headers({"content-type": "application/json"}),
            metadata={"timeout": 30},
        )

        # Override URL and method for cache
        wrapped = WrappedRequest(
            original,
            url="http://normalized-endpoint/api/users",
            method="GET",  # Hypothetical: normalize POST to GET for cache
        )

        # Verify wrapped has overrides
        assert wrapped.url == "http://normalized-endpoint/api/users"
        assert wrapped.method == "GET"

        # Unwrapped request is original, completely unchanged
        unwrapped = wrapped.unwrap()
        assert unwrapped is original
        assert unwrapped.method == "POST"
        assert unwrapped.url == "http://backend1.local/api/users"
        assert unwrapped.headers == Headers({"content-type": "application/json"})
        assert unwrapped.metadata == {"timeout": 30}

    def test_load_balanced_backends_share_cache_key(self):
        """Different backend URLs normalize to same URL for shared cache."""
        # Two requests to different backends
        request1 = Request(method="GET", url="http://backend1.local:8001/api/users")
        request2 = Request(method="GET", url="http://backend2.local:8002/api/users")

        # Same normalized URL for both
        normalized_url = "http://api-cluster/api/users"
        wrapped1 = WrappedRequest(request1, url=normalized_url)
        wrapped2 = WrappedRequest(request2, url=normalized_url)

        # Both wrapped requests have identical URL (same cache key)
        assert wrapped1.url == wrapped2.url == normalized_url

        # But original requests are different (for actual transmission)
        assert wrapped1.unwrap().url == "http://backend1.local:8001/api/users"
        assert wrapped2.unwrap().url == "http://backend2.local:8002/api/users"

    def test_dataclasses_replace_preserves_wrapped_request(self):
        """dataclasses.replace() works correctly and preserves the wrapped request.

        This is critical for hishel's cache revalidation which uses replace()
        to add conditional headers (If-None-Match, If-Modified-Since).
        """
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        # Simulate what hishel does during revalidation
        new_headers = Headers({"accept": "application/json", "if-none-match": '"etag123"'})
        replaced = replace(wrapped, headers=new_headers)

        # Replaced instance should have new headers
        assert replaced.headers == new_headers
        # But preserve the normalized URL
        assert replaced.url == "http://normalized-endpoint/api/users"
        # And still be a WrappedRequest that can unwrap to original
        assert isinstance(replaced, WrappedRequest)
        assert replaced.unwrap() is original
        assert replaced.unwrap().url == "http://backend1.local/api/users"

    def test_dataclasses_replace_with_url_change(self):
        """dataclasses.replace() with URL change updates the wrapped URL."""
        original = Request(
            method="GET",
            url="http://backend1.local/api/users",
            headers=Headers({"accept": "application/json"}),
        )

        wrapped = WrappedRequest(original, url="http://normalized-endpoint/api/users")

        # Replace with new URL
        replaced = replace(wrapped, url="http://different-endpoint/api/users")

        # URL should be updated
        assert replaced.url == "http://different-endpoint/api/users"
        # But original is still preserved
        assert replaced.unwrap() is original
        assert replaced.unwrap().url == "http://backend1.local/api/users"
