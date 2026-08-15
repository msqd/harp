"""Heuristic freshness is off by default (RFC 9111 §4.2.2 is opt-in for HARP).

RFC 9111 lets a shared cache invent a freshness lifetime for a response that carries no
explicit expiry, from its ``Last-Modified`` date. HARP does not do that by default, and has
not since 0.9 (which passed ``allow_heuristics: False`` to hishel 0.1's controller).

The reason is a trust boundary rather than compliance. HARP's cache key is derived from the
request URL alone, so no request header takes part in it. RFC 9111 makes a shared cache
refuse to reuse a response to a request carrying ``Authorization``, but it says nothing about
the many other ways an API authenticates its callers: a session cookie, ``X-Api-Key``, a
bearer token in a vendor header. When such an upstream answers with a ``Last-Modified`` and no
``Cache-Control`` at all, heuristics would make HARP hand one caller's response to the next
one.
"""

from datetime import UTC, datetime, timedelta

import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage


def _http_date(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _client(*, allow_heuristics=False):
    """Build a client caching through HARP's own storage, as a running proxy does."""
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=AsyncStorage(MemoryBlobStorage(), allow_heuristics=allow_heuristics),
        policy=SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
        ),
    )
    return AsyncClient(transport=transport)


def _counting_route(url, headers):
    """Mock ``url`` so each call answers with a body naming the call that produced it."""
    calls = {"n": 0}

    def respond(request):
        calls["n"] += 1
        return Response(200, content=f"body-{calls['n']}".encode(), headers=headers)

    respx.get(url).mock(side_effect=respond)
    return calls


@pytest.mark.asyncio
class TestHeuristicFreshnessIsOptIn:
    @respx.mock
    async def test_last_modified_alone_does_not_make_a_response_reusable(self):
        """A response whose only freshness hint is ``Last-Modified`` is not served from cache."""
        calls = _counting_route(
            "http://example.com/resource",
            {"last-modified": _http_date(timedelta(days=-30))},
        )

        async with _client() as client:
            first = await client.get("http://example.com/resource")
            second = await client.get("http://example.com/resource")

        assert calls["n"] == 2
        assert first.content == b"body-1"
        assert second.content == b"body-2"

    @respx.mock
    async def test_credentialed_callers_do_not_see_each_others_responses(self):
        """Two callers authenticating with different keys get their own upstream response.

        The credential is invisible to the cache key, so heuristics would collide them.
        """
        calls = _counting_route(
            "http://example.com/me",
            {"last-modified": _http_date(timedelta(days=-30))},
        )

        async with _client() as client:
            alice = await client.get("http://example.com/me", headers={"x-api-key": "alice"})
            bob = await client.get("http://example.com/me", headers={"x-api-key": "bob"})

        assert calls["n"] == 2
        assert alice.content == b"body-1"
        assert bob.content == b"body-2"

    @respx.mock
    async def test_an_explicit_expiry_is_still_honoured(self):
        """Turning heuristics off leaves ordinary, explicitly cacheable responses cached."""
        calls = _counting_route(
            "http://example.com/resource",
            {"cache-control": "max-age=3600"},
        )

        async with _client() as client:
            first = await client.get("http://example.com/resource")
            second = await client.get("http://example.com/resource")

        assert calls["n"] == 1
        assert first.content == b"body-1"
        assert second.content == b"body-1"

    @respx.mock
    async def test_expires_header_alone_is_still_honoured(self):
        """``Expires`` is an explicit expiry, not a heuristic, so it still caches."""
        calls = _counting_route(
            "http://example.com/resource",
            {
                "date": _http_date(timedelta()),
                "expires": _http_date(timedelta(hours=1)),
            },
        )

        async with _client() as client:
            await client.get("http://example.com/resource")
            second = await client.get("http://example.com/resource")

        assert calls["n"] == 1
        assert second.content == b"body-1"

    @respx.mock
    async def test_heuristics_can_be_turned_back_on(self):
        """Opting in restores the RFC 9111 §4.2.2 default for anyone who wants it."""
        calls = _counting_route(
            "http://example.com/resource",
            {"last-modified": _http_date(timedelta(days=-30))},
        )

        async with _client(allow_heuristics=True) as client:
            await client.get("http://example.com/resource")
            second = await client.get("http://example.com/resource")

        assert calls["n"] == 1
        assert second.content == b"body-1"
