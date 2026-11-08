"""Concurrent misses for one variant of a resource are one origin fetch (#947).

The first request to miss is the *leader* of a :class:`Flight`; the requests for the same variant that arrive while it
is in flight wait for it, then read what it stored. A waiter never fails because of a flight: it waits for a bounded
time, and when the leader fails, times out, or has nothing to share, it fetches on its own.
"""

import asyncio
import collections
import time
import typing as tp
from dataclasses import replace

from hishel import Request, Response

from harp_apps.http_cache.streams import aclose_source
from harp_apps.storage.constants import DEFAULT_MAX_RECORDED_BODY_SIZE

#: Response metadata key set once the response body is stored: what the waiters of a flight are waiting for.
STORED_METADATA = "harp_cache_stored"

#: Request metadata key holding the endpoint's recording cap: the cache stores no body larger.
MAX_BODY_SIZE_METADATA = "harp_max_recorded_body_size"

DEFAULT_TIMEOUT = 30.0


def _vary_names(response: Response) -> frozenset[str]:
    values = response.headers.get_list("vary") or []
    return frozenset(name.strip().lower() for value in values for name in value.split(",") if name.strip())


def _declared_size(response: Response) -> int:
    value = response.headers.get("content-length")
    return int(value) if value is not None and value.isdigit() else 0


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
        #: Set when a waiter gave up on it: it takes no new waiter.
        self.expired = False

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
            if not await self._wait(flight.finished, deadline):
                flight.expired = True
                return await send(request)
            if not flight.shareable:
                return await send(request)

    async def _flight_to_wait_for(
        self, slot: tuple[str, str], request: Request, deadline: float
    ) -> tp.Optional[Flight]:
        while True:
            flights = self._flights.get(slot, [])
            # Until a leader's response is known, nobody can tell which variant it fetches.
            undescribed = next(
                (flight for flight in flights if not flight.described.is_set() and not flight.expired), None
            )
            if undescribed is None:
                return next(
                    (
                        flight
                        for flight in flights
                        if not flight.finished.is_set() and not flight.expired and flight.serves(request)
                    ),
                    None,
                )
            if not await self._wait(undescribed.described, deadline):
                undescribed.expired = True
                return undescribed
            if undescribed.serves(request):
                return undescribed  # even if it has finished since: how it ended is for the waiter to read

    async def _wait(self, event: asyncio.Event, deadline: float) -> bool:
        try:
            await asyncio.wait_for(event.wait(), max(deadline - time.monotonic(), 0))
        except asyncio.TimeoutError:
            return False
        return True

    async def _lead(self, slot, request: Request, send) -> Response:
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
        limit = request.metadata.get(MAX_BODY_SIZE_METADATA) or DEFAULT_MAX_RECORDED_BODY_SIZE
        if _declared_size(response) > limit:
            self._release(slot, flight)  # never stored: no use reading it ahead of its client
            return response
        release = lambda shareable: self._release(slot, flight, shareable)  # noqa: E731
        return replace(response, stream=_ReadAhead(response, release, limit))

    def _release(self, slot: tuple[str, str], flight: Flight, shareable: bool = False) -> None:
        flights = self._flights.get(slot, [])
        if flight in flights:
            flights.remove(flight)
        if not flights:
            self._flights.pop(slot, None)
        flight.finish(shareable)


class _ReadAhead:
    """The body of a fetched response, read to its end for the cache whatever the pace of its client.

    The flight ends once the cache has the body, not once the client has it. At most ``limit`` bytes are held for a slow
    client: a body larger than that is not stored, so its flight ends with nothing to share and the read goes on at the
    client's pace.
    """

    def __init__(self, response: Response, release: tp.Callable[[bool], None], limit: int):
        self._metadata = response.metadata
        self._source = response.stream
        self._release = release
        self._limit = limit
        self._chunks: collections.deque[bytes] = collections.deque()
        self._buffered = 0
        self._error: tp.Optional[Exception] = None
        self._done = False
        self._changed = asyncio.Event()
        self._consumed = asyncio.Event()
        self._pump = asyncio.ensure_future(self._read())

    async def _read(self) -> None:
        try:
            async for chunk in self._source:
                self._chunks.append(chunk)
                self._buffered += len(chunk)
                self._changed.set()
                if self._buffered > self._limit:
                    self._release(False)
                    while self._buffered > self._limit:
                        self._consumed.clear()
                        await self._consumed.wait()
        except asyncio.CancelledError:
            self._release(False)
            raise
        except Exception as exc:
            self._error = exc
            self._release(False)
        else:
            self._release(bool(self._metadata.get(STORED_METADATA)))
        finally:
            self._done = True
            self._changed.set()

    def __aiter__(self) -> "_ReadAhead":
        return self

    async def __anext__(self) -> bytes:
        while not self._chunks and not self._done:
            self._changed.clear()
            await self._changed.wait()
        if self._chunks:
            chunk = self._chunks.popleft()
            self._buffered -= len(chunk)
            self._consumed.set()
            return chunk
        if self._error is not None:
            raise self._error
        raise StopAsyncIteration

    async def aclose(self) -> None:
        self._pump.cancel()
        await asyncio.gather(self._pump, return_exceptions=True)
        self._release(False)
        await aclose_source(self._source)
