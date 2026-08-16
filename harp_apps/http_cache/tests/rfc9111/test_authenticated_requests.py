"""Test storage of responses to authenticated requests, per RFC 9111 §3.5.

RFC 9111 §3.5 is the rule that keeps a shared cache from handing one caller's authenticated
response to the next one. HARP is a shared cache in front of other people's APIs, so it is the
section with the most to lose: the cache key is derived from the request URL alone, and an
``Authorization`` header does not appear in it.

These tests assert on what the next caller receives, not on what the first caller's response
looked like, because the failure this section exists to prevent is only visible from the second
request onwards.
"""

import pytest
import respx
from httpx import Request

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    assert_not_cached,
    make_cacheable_response,
)

URL = "http://example.com/account"


def _echo_authorization(public: bool = False):
    """An origin whose body identifies the caller it answered."""

    def handler(request: Request) -> object:
        who = request.headers.get("authorization", "anonymous")
        return make_cacheable_response(
            content=f"data for {who}".encode(),
            max_age=3600,
            public=public,
        )

    return handler


@pytest.mark.asyncio
class TestAuthenticatedRequests:
    """Tests for storing responses to authenticated requests per RFC 9111 §3.5."""

    @respx.mock
    async def test_authenticated_response_is_not_shared_rfc9111_3_5(self, cached_client, mock_storage):
        """RFC 9111 §3.5: a shared cache must not reuse a response to an authenticated request.

        Quote from RFC:
        > A shared cache MUST NOT use a cached response to a request with an
        > Authorization header field to satisfy any subsequent request unless a
        > cache directive that allows such responses to be stored is present in
        > the response.
        """
        # Arrange: an origin that answers each caller with their own data
        route = respx.get(URL).mock(side_effect=_echo_authorization())

        # Act: two different callers ask for the same URL
        alice = await cached_client.get(URL, headers={"Authorization": "Bearer alice"})
        bob = await cached_client.get(URL, headers={"Authorization": "Bearer bob"})

        # Assert: Bob gets Bob's data. Serving Alice's body here is the whole failure.
        assert alice.content == b"data for Bearer alice"
        assert bob.content == b"data for Bearer bob"

        # Assert: nothing was retained, so the origin authenticated each caller itself
        assert route.call_count == 2
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_public_lets_an_authenticated_response_be_shared_rfc9111_3_5(self, cached_client, mock_storage):
        """RFC 9111 §3.5: ``public`` is one of the directives that permits storing it anyway.

        This is the control for the test above. Without it, a cache that simply refused to store
        anything carrying ``Authorization`` would look correct, and it would be wrong in the other
        direction: the origin is allowed to say that this particular response is shareable.
        """
        # Arrange: the same origin, now marking its answers public
        route = respx.get(URL).mock(side_effect=_echo_authorization(public=True))

        # Act: two different callers ask for the same URL
        alice = await cached_client.get(URL, headers={"Authorization": "Bearer alice"})
        bob = await cached_client.get(URL, headers={"Authorization": "Bearer bob"})

        # Assert: the origin said this may be shared, so Bob legitimately gets the stored answer
        assert alice.content == b"data for Bearer alice"
        assert bob.content == b"data for Bearer alice"

        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)
