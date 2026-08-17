"""Unit tests for AsyncStorage's entry-id to cache-key index.

hishel addresses entries by UUID; this store addresses blobs by cache key. The index that
bridges the two is what makes ``update_entry`` and ``remove_entry`` able to do anything at all,
so both the resolving path and the failing path are covered here.
"""

import uuid

import pytest
from dataclasses import replace
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable

from harp_apps.http_cache.storages import KEY_INDEX_SIZE, AsyncStorage
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

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
def storage():
    return AsyncStorage(MemoryBlobStorage())


@pytest.mark.asyncio
class TestUpdateEntry:
    async def test_update_entry_rewrites_the_stored_entry(self, storage):
        """The headers hishel hands back on a 304 reach the stored blob.

        Asserted by reading the entry back out of storage rather than from the return value:
        a method that returned a correctly updated object without writing it would satisfy
        the caller and still freshen nothing.
        """
        created = await storage.create_entry(_request(), _response(), "key-1")

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
        created = await storage.create_entry(_request(), _response(), "key-1")
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
        """The index survives a round trip through storage, which is how hishel reaches it.

        In production the entry hishel updates comes from ``get_entries``, not from
        ``create_entry``, so a version of this that only indexed on create would pass the test
        above and fail in the proxy.
        """
        await storage.create_entry(_request(), _response(), "key-1")

        fresh_storage = AsyncStorage(storage._storage)
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

    async def test_an_unknown_id_returns_none_and_says_so_loudly(self, storage, caplog):
        """An index miss is the defect coming back, so it must not pass in silence.

        A miss means the 304 freshens nothing and the entry revalidates on every subsequent
        request. The symptom is a cache that looks slow rather than broken, so this warning is
        the only thing that would connect the two.
        """
        unknown = uuid.uuid4()

        with caplog.at_level("WARNING"):
            result = await storage.update_entry(unknown, lambda entry: entry)

        assert result is None
        assert any(str(unknown) in record.getMessage() for record in caplog.records), (
            "an index miss produced no warning naming the entry"
        )


@pytest.mark.asyncio
class TestRemoveEntry:
    async def test_remove_entry_deletes_the_stored_entry(self, storage):
        created = await storage.create_entry(_request(), _response(), "key-1")
        assert len(await storage.get_entries("key-1")) == 1

        await storage.remove_entry(created.id)

        assert await storage.get_entries("key-1") == []

    async def test_removing_an_unknown_id_is_harmless_and_says_so_loudly(self, storage, caplog):
        """Paired with the test above so "nothing was deleted" cannot be read as "it worked"."""
        created = await storage.create_entry(_request(), _response(), "key-1")
        unknown = uuid.uuid4()

        with caplog.at_level("WARNING"):
            await storage.remove_entry(unknown)

        assert any(str(unknown) in record.getMessage() for record in caplog.records)
        # The entry that does exist was not touched.
        assert len(await storage.get_entries("key-1")) == 1
        assert (await storage.get_entries("key-1"))[0].id == created.id


@pytest.mark.asyncio
class TestKeyIndexBound:
    async def test_the_index_is_bounded(self, storage):
        """The index must not grow with the number of entries ever stored.

        It exists to bridge one request cycle, not to mirror the cache.
        """
        for i in range(KEY_INDEX_SIZE + 50):
            await storage.create_entry(_request(f"http://endpoint/{i}"), _response(), f"key-{i}")

        assert len(storage._keys_by_id) == KEY_INDEX_SIZE

    async def test_the_most_recently_seen_entry_survives_eviction(self, storage):
        """Eviction is least-recently-used, so the entry currently in flight is the last to go."""
        first = await storage.create_entry(_request("http://endpoint/first"), _response(), "key-first")

        for i in range(KEY_INDEX_SIZE - 1):
            await storage.create_entry(_request(f"http://endpoint/{i}"), _response(), f"key-{i}")

        # Touching it moves it back to the front, the way `get_entries` does mid-cycle.
        assert storage._key_for(first.id, "update") == "key-first"

        await storage.create_entry(_request("http://endpoint/overflow"), _response(), "key-overflow")

        assert storage._key_for(first.id, "update") == "key-first"
