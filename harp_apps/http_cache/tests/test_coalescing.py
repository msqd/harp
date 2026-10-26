"""Concurrent misses for one resource are one origin fetch (#947)."""

import asyncio
import time

import httpx
import pytest
import respx
from hishel import Headers, Request, Response, SpecificationPolicy

from harp_apps.http_cache.coalescing import MAX_BODY_SIZE_METADATA, Coalescer
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.http_cache.records import MemoryCacheRecords

URL = "http://origin.test/resource"
CLIENTS = 20
CACHEABLE = {"cache-control": "max-age=300"}


class Origin:
    """Counts the fetches that reach it, and how many are in flight at once."""

    def __init__(self, *, delay=0.05, body_delay=None, headers=CACHEABLE, status=200, error=None, vary=None):
        self.delay, self.headers, self.status, self.error, self.vary = delay, headers, status, error, vary
        self.body_delay = delay if body_delay is None else body_delay
        self.fetches = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.fetches += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.in_flight -= 1
        if self.error:
            raise self.error
        headers = dict(self.headers)
        if self.vary:
            headers["vary"] = self.vary
        accept = request.headers.get("accept", "")
        return httpx.Response(self.status, headers=headers, stream=self._body(f"body for {accept}".encode()))

    async def _body(self, body: bytes):
        """The body arrives after the headers: the entry is stored only then."""
        yield body[:5]
        await asyncio.sleep(self.body_delay)
        yield body[5:]


def _client(harp_extensions=None, **transport_options) -> httpx.AsyncClient:
    transport = AsyncCacheTransport(
        next_transport=httpx.AsyncHTTPTransport(),
        storage=AsyncStorage(MemoryCacheRecords()),
        policy=SpecificationPolicy(),
        **transport_options,
    )

    async def endpoint(request: httpx.Request) -> None:
        request.extensions.setdefault("harp", {"endpoint": "test-endpoint", **(harp_extensions or {})})

    return httpx.AsyncClient(transport=transport, event_hooks={"request": [endpoint]})


async def _get_all(client: httpx.AsyncClient, accepts: list[str], url: str = URL):
    return await asyncio.gather(
        *(client.get(url, headers={"accept": accept}) for accept in accepts), return_exceptions=True
    )


@pytest.mark.asyncio
class TestCoalescing:
    async def test_concurrent_misses_are_one_origin_fetch(self):
        origin = Origin()
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                responses = await _get_all(client, ["x/y"] * CLIENTS)

        assert origin.fetches == 1
        assert [r.status_code for r in responses] == [200] * CLIENTS
        assert {r.content for r in responses} == {b"body for x/y"}

    async def test_the_waiters_are_served_from_the_stored_entry(self):
        origin = Origin()
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                responses = await _get_all(client, [""] * 3)

        assert sorted(r.extensions["hishel_from_cache"] for r in responses) == [False, True, True]

    async def test_a_failing_origin_is_answered_to_every_client(self):
        origin = Origin(error=httpx.ConnectError("down"))
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                responses = await _get_all(client, [""] * CLIENTS)

        assert all(isinstance(r, httpx.ConnectError) for r in responses)
        assert origin.fetches == CLIENTS

    async def test_an_error_response_is_answered_to_every_client(self):
        origin = Origin(status=500, headers={})
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                responses = await _get_all(client, [""] * CLIENTS)

        assert [r.status_code for r in responses] == [500] * CLIENTS
        assert origin.fetches == CLIENTS

    async def test_a_response_that_cannot_be_stored_releases_the_waiters_together(self):
        origin = Origin(headers={"cache-control": "no-store"})
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                await _get_all(client, [""] * CLIENTS)

        assert origin.fetches == CLIENTS
        assert origin.max_in_flight > 1

    async def test_a_response_the_cache_does_not_retain_releases_the_waiters_together(self):
        origin = Origin(headers={})  # no freshness information: the storage keeps nothing
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                await _get_all(client, [""] * CLIENTS)

        assert origin.max_in_flight > 1

    async def test_a_body_too_large_to_store_releases_the_waiters_together(self):
        origin = Origin()
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client({"max_recorded_body_size": 3}) as client:
                await _get_all(client, [""] * CLIENTS)

        assert origin.max_in_flight > 1

    async def test_a_waiter_gives_up_on_a_leader_that_takes_too_long(self):
        origin = Origin(delay=0.3)
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client(coalescing_timeout=0.05) as client:
                responses = await _get_all(client, [""] * 3)

        assert [r.status_code for r in responses] == [200] * 3
        assert origin.fetches == 3

    async def test_variants_are_coalesced_each_on_its_own(self):
        origin = Origin(vary="Accept")
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                responses = await _get_all(client, ["a/b", "c/d"] * 10)

        assert origin.fetches == 2
        assert [r.content for r in responses] == [b"body for a/b", b"body for c/d"] * 10

    async def test_another_variant_does_not_wait_for_a_body_in_flight(self):
        origin = Origin(vary="Accept", body_delay=0.6)
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                first = asyncio.create_task(client.get(URL, headers={"accept": "a/b"}))
                await asyncio.sleep(0.2)  # the first response has its headers, and is still arriving
                started = time.monotonic()
                await client.get(URL, headers={"accept": "c/d"})
                waited = time.monotonic() - started
                await first

        assert waited < 0.9

    async def test_other_resources_are_not_coalesced(self):
        origin = Origin()
        with respx.mock:
            respx.get(url__startswith="http://origin.test/").mock(side_effect=origin)
            async with _client() as client:
                await asyncio.gather(client.get(URL + "-1"), client.get(URL + "-2"))

        assert origin.fetches == 2

    async def test_a_warm_entry_is_not_serialized(self):
        origin = Origin()
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client() as client:
                await client.get(URL)
                responses = await _get_all(client, [""] * CLIENTS)

        assert origin.fetches == 1
        assert all(r.extensions["hishel_from_cache"] for r in responses)


@pytest.mark.asyncio
class TestStalledLeader:
    async def test_a_leader_whose_client_stalls_delays_no_follower(self):
        origin = Origin(delay=0.01, body_delay=0.01)
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client(coalescing_timeout=2.0) as client:
                async with client.stream("GET", URL) as leader:
                    chunks = leader.aiter_raw()
                    await anext(chunks)  # the leader's client reads a first chunk, then stalls
                    waits = []
                    for _ in range(3):
                        started = time.monotonic()
                        follower = await client.get(URL)
                        waits.append(time.monotonic() - started)

        assert max(waits) < 1.0
        assert origin.fetches == 1
        assert follower.extensions["hishel_from_cache"]

    async def test_a_flight_that_timed_out_a_waiter_accepts_no_new_joiner(self):
        origin = Origin(delay=0.01, body_delay=1.0)
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client(coalescing_timeout=0.1) as client:
                leader = asyncio.create_task(client.get(URL))
                await asyncio.sleep(0.05)
                waiter = asyncio.create_task(client.get(URL))  # waits 0.1 s, then fetches on its own
                await asyncio.sleep(0.2)
                started = time.monotonic()
                async with client.stream("GET", URL):
                    waited = time.monotonic() - started
                await asyncio.gather(leader, waiter)

        assert waited < 0.05


def _chunked(chunks: int, headers=CACHEABLE, size: int = 4):
    """A cacheable response of ``chunks`` 4-byte chunks, and how many chunks have been read from it."""
    read = []

    async def body():
        for _ in range(chunks):
            read.append(1)
            yield b"x" * size

    async def send(request):
        return Response(status_code=200, headers=Headers(headers), stream=body(), metadata={"hishel_stored": True})

    return send, read


def _request(cap: int | None) -> Request:
    return Request(method="GET", url=URL, metadata={MAX_BODY_SIZE_METADATA: cap})


@pytest.mark.asyncio
class TestReadAhead:
    async def test_a_body_larger_than_the_cap_follows_its_client(self):
        send, read = _chunked(10)

        response = await Coalescer().run("k", _request(8), send)
        await asyncio.sleep(0.05)

        assert len(read) < 10
        assert [chunk async for chunk in response.stream] == [b"xxxx"] * 10

    async def test_a_body_within_the_cap_is_read_ahead_of_its_client(self):
        send, read = _chunked(10)

        response = await Coalescer().run("k", _request(64), send)
        await asyncio.sleep(0.05)

        assert len(read) == 10
        assert [chunk async for chunk in response.stream] == [b"xxxx"] * 10

    async def test_a_cap_above_the_default_allows_a_larger_read_ahead(self):
        send, read = _chunked(3, size=1024 * 1024)

        await Coalescer().run("k", _request(8 * 1024 * 1024), send)
        await asyncio.sleep(0.05)

        assert len(read) == 3

    async def test_a_body_declared_larger_than_the_cap_is_not_read_ahead(self):
        send, read = _chunked(10, {**CACHEABLE, "content-length": "40"})

        response = await Coalescer().run("k", _request(8), send)
        await asyncio.sleep(0.05)

        assert read == []
        assert [chunk async for chunk in response.stream] == [b"xxxx"] * 10


@pytest.mark.asyncio
class TestSlowHeaders:
    async def test_a_flight_that_timed_out_a_waiter_before_its_headers_takes_no_new_waiter(self):
        origin = Origin(delay=3.0)
        with respx.mock:
            respx.get(URL).mock(side_effect=origin)
            async with _client(coalescing_timeout=1.0) as client:
                leader = asyncio.create_task(client.get(URL))
                await asyncio.sleep(0.05)
                waiter = asyncio.create_task(client.get(URL))
                await asyncio.sleep(1.2)  # the waiter has given up on the flight, whose headers are not there yet
                started = time.monotonic()
                late = asyncio.create_task(client.get(URL))
                await asyncio.sleep(0.2)
                waited = time.monotonic() - started
                late.cancel()
                await asyncio.gather(leader, waiter, return_exceptions=True)

        assert origin.fetches == 3
        assert waited < 0.5
