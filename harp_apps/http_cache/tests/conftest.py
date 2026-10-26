"""Test fixtures for http_cache tests."""

import asyncio
import dataclasses
import time
import uuid
from asyncio import get_running_loop
from collections.abc import AsyncIterable, AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Optional, Union

import pytest
from hishel import AsyncBaseStorage, Entry, EntryMeta
from hishel._utils import make_async_iterator
from httpcore import Request as HttpcoreRequest
from httpcore import Response as HttpcoreResponse
from httpx import AsyncBaseTransport, Request, Response
from hypercorn import Config
from hypercorn.asyncio import serve
from testcontainers.redis import AsyncRedisContainer

from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.stub_api import stub_api
from harp_apps.http_cache import models  # noqa: F401  (the tables must be on storage's Base before the schema is created)
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.records.redis import RedisCacheRecords
from harp_apps.http_cache.records.sql import SqlCacheRecords
from harp.utils.testing.databases import TEST_DATABASES
from harp_apps.storage.conftest import *  # noqa
from harp_apps.storage.conftest import migrated_engine
from harp_apps.storage.utils.testing.sql import create_database_container_for


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
        self.updated_ids: list[uuid.UUID] = []
        self.removed_ids: list[uuid.UUID] = []

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
        id: uuid.UUID,
        new_entry: Union[Entry, Callable[[Entry], Entry]],
    ) -> Optional[Entry]:
        """Update an existing entry, addressed by id, the way hishel addresses it.

        The previous signature took ``(entry, request, response)``, which hishel never calls,
        so every test that appeared to cover the update path raised ``TypeError`` instead of
        asserting anything. See https://github.com/msqd/harp/issues/908.
        """
        for key, entries in self.entries.items():
            for index, entry in enumerate(entries):
                if entry.id != id:
                    continue
                updated = new_entry if isinstance(new_entry, Entry) else new_entry(entry)
                entries[index] = updated
                self.updated_ids.append(id)
                return updated
        return None

    async def remove_entry(self, id: uuid.UUID) -> None:
        """Remove an entry, addressed by id, the way hishel addresses it."""
        for entries in self.entries.values():
            for entry in list(entries):
                if entry.id == id:
                    entries.remove(entry)
                    self.removed_ids.append(id)
                    return

    async def stamp(self) -> int:
        return 0

    async def invalidate(self, key: str, *, mode) -> None:
        """Drop every entry of a key, as the real storage does."""
        for entry in await self.get_entries(key):
            await self.remove_entry(entry.id)

    async def close(self) -> None:
        """Close storage."""
        pass


class MockTransport(AsyncBaseTransport):
    """Mock underlying transport that returns canned responses."""

    def __init__(self):
        self.request_count = 0
        self.last_request: Optional[Request] = None
        self.cache_control = "max-age=3600"

    async def handle_async_request(self, request: Request) -> Response:
        """Return a mock response."""
        self.request_count += 1
        self.last_request = request
        return Response(
            status_code=200,
            headers={
                "content-type": "application/json",
                "cache-control": self.cache_control,
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


@pytest.fixture(scope="session")
def redis_container():
    """A Redis server, for the whole session."""
    with AsyncRedisContainer() as container:
        yield container


@pytest.fixture
def redis_url(redis_container):
    return f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"


@asynccontextmanager
async def emptied(container: AsyncRedisContainer):
    """A client of a Redis server, which holds nothing."""
    client = await container.get_async_client()
    try:
        await client.flushall()
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def redis_client(redis_container):
    async with emptied(redis_container) as client:
        yield client


@pytest.fixture(scope="session", params=["memory", "redis", *TEST_DATABASES])
def cache_backend(request):
    """What each records backend runs on: nothing for the memory one, a Redis container, a database url."""
    if request.param == "memory":
        yield None
    elif request.param == "redis":
        yield request.getfixturevalue("redis_container")
    else:
        dialect, image, driver = request.param.split("|")
        yield from create_database_container_for(dialect, image, driver)


@pytest.fixture
async def records(cache_backend, test_id):
    """Every records backend, for the behaviour they all promise."""
    if cache_backend is None:
        yield MemoryCacheRecords()
    elif isinstance(cache_backend, AsyncRedisContainer):
        async with emptied(cache_backend) as client:
            yield RedisCacheRecords(client)
    else:
        async with migrated_engine(cache_backend, test_id) as engine:
            yield SqlCacheRecords(engine)
