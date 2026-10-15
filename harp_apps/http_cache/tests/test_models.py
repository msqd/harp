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

        unwrapped = wrapped.unwrap()
        assert unwrapped.method == original.method
        assert unwrapped.url == original.url
        assert unwrapped.headers == original.headers

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

    def test_unwrap_undoes_the_cache_key_overrides(self):
        """unwrap() addresses the real origin, whatever was overridden for the cache key.

        ``method`` and ``url`` are the attributes this class overrides for cache-key
        normalization, so both come back from the wrapped request.
        """
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

        # Unwrapped request addresses the backend as it really is
        unwrapped = wrapped.unwrap()
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

    def test_conditional_headers_added_by_replace_survive_unwrap(self):
        """The conditional headers hishel adds during revalidation reach the origin.

        This is the unit-level statement of the defect in
        https://github.com/msqd/harp/issues/906. hishel revalidates by calling
        ``replace(request, headers={..., "if-none-match": ...})``, and ``replace()`` carries
        this object's metadata through untouched. The wrapped request held in that metadata is
        therefore the request as it was *before* the conditional headers existed, so returning
        it from ``unwrap()`` sends a revalidation with no validator at all and the origin has
        no choice but to answer 200 with the whole body.

        The previous version of this test asserted ``replaced.unwrap() is original``, which is
        precisely the behaviour that breaks revalidation, under a docstring saying the test
        existed to protect revalidation.
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

        # The cache still sees the normalized URL, so the cache key is unaffected.
        assert isinstance(replaced, WrappedRequest)
        assert replaced.headers == new_headers
        assert replaced.url == "http://normalized-endpoint/api/users"

        # And the request actually sent carries the validator, addressed at the real backend.
        unwrapped = replaced.unwrap()
        assert unwrapped.url == "http://backend1.local/api/users"
        assert unwrapped.headers["if-none-match"] == '"etag123"'
        assert unwrapped.headers["accept"] == "application/json"

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
        # But the request sent upstream still addresses the real backend
        assert replaced.unwrap().url == "http://backend1.local/api/users"
