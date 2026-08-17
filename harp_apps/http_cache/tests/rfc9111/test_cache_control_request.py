"""Test Cache-Control request directives compliance with RFC 9111 §5.2.1.

This module verifies that HARP's HTTP caching honours the directives a *client*
sends on a request, as opposed to those an origin sends on a response (covered by
``test_cache_control_response.py``).

RFC 9111 §5.2.1 defines request directives. The two that bind a shared cache's
store and reuse decisions are ``no-store`` (§5.2.1.5) and ``no-cache`` (§5.2.1.4).
"""

import pytest
import respx

from harp_apps.http_cache.tests.rfc9111.conftest import (
    assert_cache_hit,
    assert_not_cached,
    make_cacheable_response,
)


@pytest.mark.asyncio
class TestRequestNoStore:
    """Tests for a client's Cache-Control: no-store per RFC 9111 §5.2.1.5."""

    @respx.mock
    async def test_ordinary_request_is_cached_control(self, cached_client, mock_storage):
        """Control: without any request directive, the same resource is cached.

        Without this, "nothing was stored" in the tests below is indistinguishable
        from a cache that is not working at all.
        """
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(content=b"cacheable", max_age=300)
        )

        response1 = await cached_client.get("http://example.com/resource")
        response2 = await cached_client.get("http://example.com/resource")

        assert response1.content == b"cacheable"
        assert response2.content == b"cacheable"
        assert route.call_count == 1, "the second request should have been served from cache"
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_no_store_prevents_storage_rfc9111_5_2_1_5(self, cached_client, mock_storage):
        """RFC 9111 §5.2.1.5: a request carrying no-store must not be stored.

        Quote from RFC:
        > The no-store request directive indicates that a cache MUST NOT store any
        > part of either this request or any response to it.

        The origin's response is explicitly cacheable (``max-age=300``), so the only
        reason not to store it is the client's directive.
        """
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(content=b"do not keep this", max_age=300)
        )

        headers = {"cache-control": "no-store"}
        response1 = await cached_client.get("http://example.com/resource", headers=headers)
        response2 = await cached_client.get("http://example.com/resource", headers=headers)

        # The client still gets the origin's response, unchanged.
        assert response1.status_code == 200
        assert response1.content == b"do not keep this"
        assert response2.content == b"do not keep this"

        # And the origin was asked both times, because nothing was ever stored.
        assert route.call_count == 2
        assert_not_cached(mock_storage)

    @respx.mock
    async def test_no_store_is_not_served_from_an_existing_entry_rfc9111_5_2_1_5(self, cached_client, mock_storage):
        """RFC 9111 §5.2.1.5: an existing entry must not answer a no-store request.

        "MUST NOT store any part of ... any response to it" binds reuse as well as
        storage: a response handed back from the cache is a stored response being
        used to answer this request. This is the other half of the directive and it
        fails independently of the storage half.
        """
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(content=b"already cached", max_age=300)
        )

        # Populate the cache with an ordinary request.
        await cached_client.get("http://example.com/resource")
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

        # A no-store request for the same resource must reach the origin.
        response = await cached_client.get("http://example.com/resource", headers={"cache-control": "no-store"})

        assert response.content == b"already cached"
        assert route.call_count == 2, "the no-store request was answered from the existing cache entry"

        # And it must not have left an entry of its own behind either.
        assert_cache_hit(mock_storage, expected_key_count=1)

    @respx.mock
    async def test_no_store_request_is_still_proxied_normally_rfc9111_5_2_1_5(self, cached_client, mock_storage):
        """A no-store request is bypassed, not degraded: the client gets the origin's response.

        Every other test in this class asserts that something is *absent* from the
        cache, and all of them would pass just as well if the bypass returned
        nothing useful at all. This one pairs those absences with a presence.
        """
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                status_code=203,
                content=b"the origin's own answer",
                max_age=300,
                etag="unchanged",
                **{"x-origin-marker": "from the origin"},
            )
        )

        response = await cached_client.get("http://example.com/resource", headers={"cache-control": "no-store"})

        assert response.status_code == 203
        assert response.content == b"the origin's own answer"
        assert response.headers["x-origin-marker"] == "from the origin"
        assert response.headers["content-type"] == "text/plain"
        assert response.headers["etag"] == '"unchanged"'
        assert response.headers["cache-control"] == "max-age=300"

    @respx.mock
    async def test_no_store_response_is_reported_as_a_cache_miss(self, cached_client, mock_storage):
        """A bypassed request is still instrumented as an ordinary miss.

        ``HttpClientProxyAdapter`` reads ``hishel_from_cache`` out of the response
        extensions to write ``X-Cache``, and the proxy controller reads the same key
        to decide whether the transaction was cached. A bypass that leaves the key
        absent emits no ``X-Cache`` header at all, so the dashboard would go wrong
        for exactly these requests.
        """
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(content=b"bypassed", max_age=300)
        )

        response = await cached_client.get("http://example.com/resource", headers={"cache-control": "no-store"})

        assert response.extensions.get("hishel_from_cache") is False
        assert response.extensions.get("hishel_stored") is False
        assert "hishel_created_at" in response.extensions

    @respx.mock
    async def test_no_store_still_drops_connection_specific_response_headers(self, cached_client, mock_storage):
        """RFC 9110 §7.6.1 still applies on the bypass path.

        The bypass must go through ``request_sender``, which is the last point at
        which ``Connection`` can be read. A bypass wired straight to the next
        transport would leak connection-specific fields to the client for no-store
        requests only, which is the one path nobody would re-probe.
        """
        respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(
                content=b"bypassed",
                max_age=300,
                connection="keep-alive, X-Origin-Secret",
                **{
                    "x-origin-secret": "leaked-via-connection-header",
                    "keep-alive": "timeout=5, max=100",
                    "trailer": "X-Origin-Trailer",
                    "upgrade": "h2c",
                    "proxy-authenticate": 'Basic realm="origin"',
                    "x-origin-plain": "kept",
                },
            )
        )

        response = await cached_client.get("http://example.com/resource", headers={"cache-control": "no-store"})

        for name in ("connection", "keep-alive", "trailer", "upgrade", "proxy-authenticate", "x-origin-secret"):
            assert name not in response.headers, f"{name} leaked to the client on the no-store bypass"

        # Paired with an "and this is", so the assertions above cannot pass by over-stripping.
        assert response.headers["x-origin-plain"] == "kept"
        assert response.headers["content-type"] == "text/plain"
        assert response.content == b"bypassed"


@pytest.mark.asyncio
class TestRequestNoCache:
    """Tests for a client's Cache-Control: no-cache per RFC 9111 §5.2.1.4."""

    @respx.mock
    async def test_no_cache_forces_revalidation_rfc9111_5_2_1_4(self, cached_client, mock_storage):
        """RFC 9111 §5.2.1.4: no-cache forces validation but allows storage.

        Quote from RFC:
        > The no-cache request directive indicates that the client prefers a stored
        > response not be used to satisfy the request without successful validation
        > on the origin server.

        This works today and goes through the same header parse as ``no-store``, so
        it is here to catch a fix for §5.2.1.5 that regresses §5.2.1.4.
        """
        route = respx.get("http://example.com/resource").mock(
            return_value=make_cacheable_response(content=b"validated", max_age=300, etag="revalidate-me")
        )

        # Populate the cache.
        await cached_client.get("http://example.com/resource")
        assert route.call_count == 1
        assert_cache_hit(mock_storage, expected_key_count=1)

        # no-cache must go back to the origin even though the entry is fresh.
        response = await cached_client.get("http://example.com/resource", headers={"cache-control": "no-cache"})

        assert response.content == b"validated"
        assert route.call_count == 2, "no-cache was answered from cache without revalidating"

        # Unlike no-store, no-cache still allows the entry to exist.
        assert len(mock_storage.entries) == 1
