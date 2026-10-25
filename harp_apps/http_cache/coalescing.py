"""Concurrent misses for one variant of a resource are one origin fetch (#947).

The first request to miss is the *leader* of a :class:`Flight`; the requests for the same variant that arrive while it
is in flight wait for it, then read what it stored. A waiter never fails because of a flight: it waits for a bounded
time, and when the leader fails, times out, or has nothing to share, it fetches on its own.
"""

import asyncio
import time
import typing as tp
from dataclasses import replace

from hishel import Request, Response

from harp_apps.http_cache.streams import aclose_source

#: Response metadata key set once the response body is stored: what the waiters of a flight are waiting for.
STORED_METADATA = "harp_cache_stored"

DEFAULT_TIMEOUT = 30.0


def _vary_names(response: Response) -> frozenset[str]:
    values = response.headers.get_list("vary") or []
    return frozenset(name.strip().lower() for value in values for name in value.split(",") if name.strip())


class Flight:
    """One origin fetch in progress, for one variant of one cache key."""

    def __init__(self, request: Request):
        self._request_headers = request.headers
        self._vary: frozenset[str] = frozenset()
        #: Set when the response headers are known, hence which variant this is.
        self.described = asyncio.Event()
        #: Set when the fetch has ended, or has nothing more to share.
        self.finished = asyncio.Event()
        #: Whether a request that waited can now read what the fetch stored.
        self.shareable = False

    def describe(self, response: Response) -> None:
        self._vary = _vary_names(response)
        self.described.set()

    def finish(self, shareable: bool) -> None:
        if not self.finished.is_set():
            self.shareable = shareable
        self.described.set()
        self.finished.set()

    def serves(self, request: Request) -> bool:
        """Whether the response being fetched is the one this request would get (RFC 9111 §4.1)."""
        if "*" in self._vary:
            return False
        return all(request.headers.get(name) == self._request_headers.get(name) for name in self._vary)


class Coalescer:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self._timeout = timeout
        self._flights: dict[tuple[str, str], list[Flight]] = {}

    async def run(self, key: str, request: Request, send: tp.Callable[[Request], tp.Awaitable[Response]]) -> Response:
        """Send the request, unless a flight already fetches what it needs: then wait for it and send afterwards."""
        slot = (key, request.method)
        deadline = time.monotonic() + self._timeout
        while True:
            flight = await self._flight_to_wait_for(slot, request, deadline)
            if flight is None:
                return await self._lead(slot, request, send)
            if not await self._wait(flight.finished, deadline) or not flight.shareable:
                return await send(request)

    async def _flight_to_wait_for(
        self, slot: tuple[str, str], request: Request, deadline: float
    ) -> tp.Optional[Flight]:
        while True:
            flights = self._flights.get(slot, [])
            # Until a leader's response is known, nobody can tell which variant it fetches.
            undescribed = next((flight for flight in flights if not flight.described.is_set()), None)
            if undescribed is None:
                return next(
                    (flight for flight in flights if not flight.finished.is_set() and flight.serves(request)), None
                )
            if not await self._wait(undescribed.described, deadline) or undescribed.serves(request):
                return undescribed  # even if it has finished since: how it ended is for the waiter to read

    async def _wait(self, event: asyncio.Event, deadline: float) -> bool:
        try:
            await asyncio.wait_for(event.wait(), max(deadline - time.monotonic(), 0))
        except asyncio.TimeoutError:
            return False
        return True

    async def _lead(self, slot, request, send) -> Response:
        flight = Flight(request)
        self._flights.setdefault(slot, []).append(flight)
        try:
            response = await send(request)
        except BaseException:
            self._release(slot, flight)
            raise
        flight.describe(response)
        if not response.metadata.get("hishel_stored"):
            # Served from the cache, or not storable: a hit for the waiters, or nothing to share with them.
            self._release(slot, flight, shareable=bool(response.metadata.get("hishel_from_cache")))
            return response
        release = lambda shareable: self._release(slot, flight, shareable)  # noqa: E731
        return replace(response, stream=_ReleasedAtEnd(response, release))

    def _release(self, slot: tuple[str, str], flight: Flight, shareable: bool = False) -> None:
        flights = self._flights.get(slot, [])
        if flight in flights:
            flights.remove(flight)
        if not flights:
            self._flights.pop(slot, None)
        flight.finish(shareable)


class _ReleasedAtEnd:
    """The body of a fetched response, ending its flight once it is read to its end, or closed.

    The flight is shareable only if the body ended in the cache: the storage says so in the response metadata.
    """

    def __init__(self, response: Response, release: tp.Callable[[bool], None]):
        self._metadata = response.metadata
        self._source = response.stream
        self._chunks = aiter(self._source)
        self._release = release

    def __aiter__(self) -> "_ReleasedAtEnd":
        return self

    async def __anext__(self) -> bytes:
        try:
            return await anext(self._chunks)
        except StopAsyncIteration:
            self._release(bool(self._metadata.get(STORED_METADATA)))
            raise
        except BaseException:
            self._release(False)
            raise

    async def aclose(self) -> None:
        self._release(False)
        await aclose_source(self._source)
