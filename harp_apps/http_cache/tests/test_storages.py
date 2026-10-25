"""Unit tests for AsyncStorage: hishel addresses entries by UUID, the records find them by it."""

from harp_apps.http_cache.tests import store_entry
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
import asyncio
import time
import uuid
from email.utils import parsedate_to_datetime

import httpx
import pytest
import respx
from dataclasses import replace
from hishel import CacheOptions, Headers, Request, Response, SpecificationPolicy
from hishel._core.models import AnyIterable

from harp_apps.http_cache.records import EndpointStats
from harp_apps.http_cache.storages import MAX_KEY_SIZE, AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport

CACHEABLE = {"cache-control": "max-age=300", "content-type": "text/plain"}


def _request(url="http://endpoint/resource"):
    return Request(method="GET", url=url, headers=Headers({}))


def _response(body=b"payload", **extra_headers):
    return Response(
        status_code=200,
        headers=Headers({**CACHEABLE, **extra_headers}),
        stream=AnyIterable(body),
        metadata={},
    )


@pytest.fixture
def storage(records):
    return AsyncStorage(records)


@pytest.mark.asyncio
class TestUpdateEntry:
    async def test_update_entry_rewrites_the_stored_entry(self, storage):
        """The headers hishel hands back on a 304 reach the stored blob.

        Asserted by reading the entry back out of storage rather than from the return value:
        a method that returned a correctly updated object without writing it would satisfy
        the caller and still freshen nothing.
        """
        created = await store_entry(storage, _request(), _response(), "key-1")

        updated = await storage.update_entry(
            created.id,
            lambda entry: replace(
                entry,
                response=replace(entry.response, headers=Headers({**CACHEABLE, "etag": '"v2"'})),
            ),
        )

        assert updated is not None
        assert updated.response.headers["etag"] == '"v2"'

        (stored,) = await storage.get_entries("key-1")
        assert stored.response.headers["etag"] == '"v2"'
        assert await stored.response.aread() == b"payload"

    async def test_update_entry_accepts_a_whole_entry(self, storage):
        """hishel's contract allows an Entry as well as a callable, so both are supported."""
        created = await store_entry(storage, _request(), _response(), "key-1")
        replacement = replace(
            created,
            response=Response(
                status_code=200,
                headers=Headers({**CACHEABLE, "etag": '"whole"'}),
                stream=AnyIterable(b"replaced"),
                metadata={},
            ),
        )

        await storage.update_entry(created.id, replacement)

        (stored,) = await storage.get_entries("key-1")
        assert stored.response.headers["etag"] == '"whole"'
        assert await stored.response.aread() == b"replaced"

    async def test_an_entry_retrieved_from_storage_can_be_updated(self, storage):
        """The entry is found by its id in the records, by a storage that never stored it.

        In production the entry hishel updates comes from ``get_entries``, and another instance
        may be the one that stored it.
        """
        await store_entry(storage, _request(), _response(), "key-1")

        fresh_storage = AsyncStorage(storage._records)
        (retrieved,) = await fresh_storage.get_entries("key-1")

        updated = await fresh_storage.update_entry(
            retrieved.id,
            lambda entry: replace(
                entry, response=replace(entry.response, headers=Headers({**CACHEABLE, "etag": '"round-trip"'}))
            ),
        )

        assert updated is not None
        (stored,) = await fresh_storage.get_entries("key-1")
        assert stored.response.headers["etag"] == '"round-trip"'

    async def test_an_unknown_id_returns_none(self, storage):
        """The entry was evicted, replaced or expired since hishel looked it up."""
        assert await storage.update_entry(uuid.uuid4(), lambda entry: entry) is None

    async def test_an_update_that_changes_the_variant_replaces_the_entry(self, storage):
        """A 304 can bring a Vary the entry did not have: it is then another variant, not a second entry."""
        created = await store_entry(storage, _request(), _response(), "key-1")

        await storage.update_entry(
            created.id,
            lambda entry: replace(
                entry, response=replace(entry.response, headers=Headers({**CACHEABLE, "vary": "Accept"}))
            ),
        )

        (stored,) = await storage.get_entries("key-1")
        assert stored.id == created.id
        assert stored.response.headers["vary"] == "Accept"

    async def test_an_update_keeps_the_entry_id(self, storage):
        created = await store_entry(storage, _request(), _response(), "key-1")

        await storage.update_entry(created.id, lambda entry: entry)

        (stored,) = await storage.get_entries("key-1")
        assert stored.id == created.id


@pytest.mark.asyncio
class TestRemoveEntry:
    async def test_remove_entry_deletes_the_stored_entry(self, storage):
        created = await store_entry(storage, _request(), _response(), "key-1")
        assert len(await storage.get_entries("key-1")) == 1

        await storage.remove_entry(created.id)

        assert await storage.get_entries("key-1") == []

    async def test_removing_an_unknown_id_is_harmless(self, storage):
        """Paired with the test above so "nothing was deleted" cannot be read as "it worked"."""
        created = await store_entry(storage, _request(), _response(), "key-1")

        await storage.remove_entry(uuid.uuid4())

        assert [entry.id for entry in await storage.get_entries("key-1")] == [created.id]


@pytest.mark.asyncio
class TestDateOnStore:
    """RFC 9110 §6.6.1: a cache storing a response without ``Date`` records its time of receipt."""

    async def test_a_response_without_date_gets_the_time_of_receipt(self, storage):
        before = int(time.time())
        await store_entry(storage, _request(), _response(), "key-1")
        after = int(time.time())

        (stored,) = await storage.get_entries("key-1")
        date = parsedate_to_datetime(stored.response.headers["date"]).timestamp()
        assert before <= date <= after

    async def test_a_response_with_date_keeps_it(self, storage):
        date = "Wed, 21 Oct 2015 07:28:00 GMT"
        await store_entry(storage, _request(), _response(date=date), "key-1")

        (stored,) = await storage.get_entries("key-1")
        assert stored.response.headers["date"] == date

    async def test_a_stored_response_still_serves_its_body(self, storage):
        await store_entry(storage, _request(), _response(), "key-1")

        (stored,) = await storage.get_entries("key-1")
        assert await stored.response.aread() == b"payload"

    @respx.mock
    async def test_max_age_expires_without_date_through_the_cache_transport(self, storage):
        route = respx.get("http://example.com/resource").mock(
            return_value=httpx.Response(200, content=b"x", headers={"cache-control": "max-age=1"})
        )
        transport = AsyncCacheTransport(
            next_transport=httpx.AsyncHTTPTransport(),
            storage=storage,
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, allow_stale=False)),
        )
        async with httpx.AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS) as client:
            await client.get("http://example.com/resource")
            await asyncio.sleep(2)
            await client.get("http://example.com/resource")

        assert route.call_count == 2


@pytest.mark.asyncio
class TestStoredRecords:
    async def test_stored_entries_are_counted_per_endpoint(self, storage, records):
        await store_entry(storage, _request("http://api/a"), _response(b"12345"), "http://api/a")
        await store_entry(storage, _request("http://web/b"), _response(b"123"), "http://web/b")

        assert await records.stats() == [EndpointStats("api", 1, 5), EndpointStats("web", 1, 3)]

    async def test_a_key_too_long_to_be_indexed_is_not_stored(self, storage, records):
        key = "http://api/" + "x" * MAX_KEY_SIZE

        entry = await store_entry(storage, _request(key), _response(), key)

        assert await entry.response.aread() == b"payload"
        assert await records.list_keys() == []

    async def test_a_refused_path_is_counted_and_warned_about_once_per_endpoint(self, storage, records, caplog):
        key = "http://api/" + "x" * MAX_KEY_SIZE
        other = key.replace("api", "web")

        with caplog.at_level("WARNING"):
            for _ in range(3):
                await store_entry(storage, _request(key), _response(), key)
            await store_entry(storage, _request(other), _response(), other)

        assert await records.stats() == [], "counted in memory, not written on the request path"
        await storage.flush_counters()
        assert await records.stats() == [EndpointStats("api", 0, 0, 3), EndpointStats("web", 0, 0, 1)]
        assert sum("path over" in record.getMessage() for record in caplog.records) == 2

    async def test_refusals_not_yet_written_are_flushed_on_close(self, storage, records):
        key = "http://api/" + "x" * MAX_KEY_SIZE
        await store_entry(storage, _request(key), _response(), key)

        await storage.close()

        assert await records.stats() == [EndpointStats("api", 0, 0, 1)]

    async def test_a_cache_debug_log_never_prints_a_query(self, storage, caplog):
        url = "http://api/items?token=s3cr3t"
        key = "http://api/items?abc"

        with caplog.at_level("DEBUG", logger="harp_apps.http_cache.storages"):
            entry = await store_entry(storage, _request(url), _response(), key)
            await storage.get_entries(key)
            await storage.update_entry(entry.id, lambda e: e)

        logged = [
            record.getMessage() for record in caplog.records if "'logger': 'harp_apps.http_cache" in record.getMessage()
        ]
        assert logged and not any("s3cr3t" in message for message in logged)

    async def test_the_query_does_not_count_in_the_cap(self, storage, records):
        key = "http://api/items?" + "x" * MAX_KEY_SIZE

        await store_entry(storage, _request(key), _response(), key)

        assert await records.list_keys() == [key]
