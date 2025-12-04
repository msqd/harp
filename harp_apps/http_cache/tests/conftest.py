"""Test fixtures for http_cache tests."""

import asyncio
import dataclasses
import time
import uuid
from asyncio import get_running_loop
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import replace
from typing import Optional

import pytest
from hishel import AsyncBaseStorage, Entry, EntryMeta
from hishel._utils import make_async_iterator
from httpcore import Request as HttpcoreRequest
from httpcore import Response as HttpcoreResponse
from httpx import AsyncBaseTransport, Request, Response
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.stub_api import stub_api


@dataclasses.dataclass
class StubServerDescription:
    host: str
    port: int

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


class MockAsyncStorage(AsyncBaseStorage):
    """Mock storage implementation for testing."""

    def __init__(self):
        super().__init__()
        self.entries: dict[str, list[Entry]] = {}
        self.contents: dict[str, bytes] = {}  # Store response bodies separately
        self.created_keys: list[str] = []

    async def create_entry(
        self,
        request: HttpcoreRequest,
        response: HttpcoreResponse,
        key: str,
        id_: Optional[object] = None,
    ) -> Entry:
        """Store an entry and track the cache key used."""
        entry_id = id_ or uuid.uuid4()

        # Read and store the response stream content
        # This mimics what real storage does (serialize/deserialize)
        if isinstance(response.stream, (AsyncIterator, AsyncIterable)):
            content = b"".join([chunk async for chunk in response.stream])
            # Store the content separately by entry ID
            self.contents[str(entry_id)] = content
            # Create a new response with a fresh stream containing the same content
            response = replace(response, stream=make_async_iterator([content]))

        entry = Entry(
            id=entry_id,
            request=request,
            response=response,
            meta=EntryMeta(created_at=time.time(), deleted_at=None),
            cache_key=key.encode("utf-8"),
            extra={"number_of_uses": 0},
        )
        self.entries.setdefault(key, []).append(entry)
        self.created_keys.append(key)
        return entry

    async def get_entries(self, key: str) -> list[Entry]:
        """Retrieve entries by cache key."""
        entries = self.entries.get(key, [])

        # Recreate streams for each retrieved entry
        # This mimics what real storage does when deserializing
        result = []
        for entry in entries:
            # Get the stored content
            content = self.contents.get(str(entry.id), b"")
            # Create a fresh response with a new stream
            fresh_response = replace(entry.response, stream=make_async_iterator([content]))
            fresh_entry = replace(entry, response=fresh_response)
            result.append(fresh_entry)

        return result

    async def update_entry(
        self,
        entry: Entry,
        request: HttpcoreRequest,
        response: HttpcoreResponse,
    ) -> Entry:
        """Update an existing entry."""
        entry.request = request
        entry.response = response
        return entry

    async def remove_entry(self, entry: Entry) -> None:
        """Remove an entry from storage."""
        for key, entries in self.entries.items():
            if entry in entries:
                entries.remove(entry)
                break

    async def close(self) -> None:
        """Close storage."""
        pass


class MockTransport(AsyncBaseTransport):
    """Mock underlying transport that returns canned responses."""

    def __init__(self):
        self.request_count = 0
        self.last_request: Optional[Request] = None

    async def handle_async_request(self, request: Request) -> Response:
        """Return a mock response."""
        self.request_count += 1
        self.last_request = request
        return Response(
            status_code=200,
            headers={
                "content-type": "application/json",
                "cache-control": "max-age=3600",
            },
            content=b'{"message": "test response"}',
        )


@pytest.fixture
async def test_api():
    """Start a test API server for cache testing."""
    shutdown_event = asyncio.Event()
    config = Config()
    host, port = "localhost", get_available_network_port()
    config.bind = [f"{host}:{port}"]

    # starts the async server in the background
    server = asyncio.ensure_future(
        serve(
            stub_api,
            config=config,
            shutdown_trigger=shutdown_event.wait,
        ),
        loop=get_running_loop(),
    )
    await asyncio.to_thread(wait_for_port, port, host)

    try:
        yield StubServerDescription(host, port)
    finally:
        shutdown_event.set()
        await server


@pytest.fixture
def mock_storage():
    """Provide a mock storage instance."""
    return MockAsyncStorage()


@pytest.fixture
def mock_transport():
    """Provide a mock underlying transport."""
    return MockTransport()
