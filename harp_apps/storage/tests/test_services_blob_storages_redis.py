from datetime import UTC, datetime, timedelta

import pytest
from redis.asyncio import Redis

from harp.config import ConfigurationBuilder
from harp.models import Blob
from harp.services import CannotResolveTypeException
from harp_apps.storage.models.blobs import ORPHAN_GRACE
from harp_apps.storage.services.blob_storages.redis import BLOB_PREFIX, RedisBlobStorage


async def test_basics(redis_blob_storage: RedisBlobStorage):
    _storage = redis_blob_storage
    assert _storage.client is not None
    blob = Blob(id="foo", data=b"bar", content_type="text/plain")

    assert _storage.type == "redis"
    assert await _storage.get("foo") is None
    assert await _storage.client.get(BLOB_PREFIX + "foo") is None

    assert await _storage.put(blob) == blob
    assert await _storage.get("foo") == blob
    assert await _storage.client.get(BLOB_PREFIX + "foo") == b"text/plain\nbar"

    assert await _storage.exists("foo")
    assert await _storage.delete("foo") is None
    assert not await _storage.exists("foo")
    assert await _storage.get("foo") is None
    assert await _storage.client.get(BLOB_PREFIX + "foo") is None


class SystemTestMixin:
    applications = []
    settings = {}

    @pytest.fixture
    async def system(self):
        system = await ConfigurationBuilder(
            {
                "applications": self.applications,
                **self.settings,
            },
            use_default_applications=False,
        ).abuild_system(validate_dependencies=False)
        try:
            yield system
        finally:
            await system.dispose()


class TestRedisBlobStorageServiceDefaults(SystemTestMixin):
    applications = ["storage"]
    settings = {
        "storage": {
            "blobs": {"type": "redis"},
        },
    }

    async def test_load_redis_blob_storage_service(self, system):
        redis = system.provider.get("storage.redis")
        assert isinstance(redis, Redis)
        assert redis.connection_pool.connection_kwargs == {
            "db": 0,
            "host": "localhost",
            "port": 6379,
        }
        assert system.provider.get("storage.blobs")


class TestRedisBlobStorageServiceCustom(SystemTestMixin):
    applications = ["storage"]
    settings = {
        "storage": {
            "blobs": {
                "type": "redis",
            },
            "redis": {
                "url": "redis://redis.example.com:1234/1",
            },
        }
    }

    async def test_load_redis_blob_storage_service(self, system):
        redis = system.provider.get("storage.redis")
        assert isinstance(redis, Redis)
        assert redis.connection_pool.connection_kwargs == {
            "db": 1,
            "host": "redis.example.com",
            "port": 1234,
        }
        assert system.provider.get("storage.blobs")


class TestRedisBlobStorageNotConfigured(SystemTestMixin):
    applications = ["storage"]
    settings = {
        "storage": {
            "blobs": {
                "type": "sql",
            },
        }
    }

    async def test_sql_does_not_load_redis_services(self, system):
        try:
            with pytest.raises(CannotResolveTypeException):
                system.provider.get("storage.redis")
        finally:
            await system.dispose()


class TestEnumeration:
    async def test_iter_blob_ids_lists_blobs_only(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))
        await redis_blob_storage.put(Blob(id="b", data=b"2", content_type="text/plain"))

        assert sorted([blob_id async for blob_id in redis_blob_storage.iter_blob_ids()]) == ["a", "b"]

    async def test_iter_blobs_filters_by_content_type(self, redis_blob_storage: RedisBlobStorage):
        meta = Blob(id="m", data=b"entry", content_type="cache/meta")
        await redis_blob_storage.put(meta)
        await redis_blob_storage.put(Blob(id="b", data=b"2", content_type="text/plain"))

        assert [blob async for blob in redis_blob_storage.iter_blobs("cache/meta")] == [meta]

    async def test_delete_blobs_spares_a_blob_stored_again_with_other_data(self, redis_blob_storage: RedisBlobStorage):
        read = Blob(id="a", data=b"old", content_type="text/plain")
        await redis_blob_storage.force_put(read)
        await redis_blob_storage.put(Blob(id="b", data=b"same", content_type="text/plain"))
        await redis_blob_storage.force_put(Blob(id="a", data=b"new", content_type="text/plain"))

        await redis_blob_storage.delete_blobs([read, Blob(id="b", data=b"same", content_type="text/plain")])

        assert (await redis_blob_storage.get("a")).data == b"new"
        assert await redis_blob_storage.get("b") is None


class TestDeleteStale:
    async def test_deletes_blobs_not_written_since(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))

        later = datetime.now(UTC) + timedelta(seconds=1)
        assert await redis_blob_storage.delete_stale(["a"], older_than=later) == 1
        assert await redis_blob_storage.get("a") is None

    async def test_keeps_blobs_written_since(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))

        earlier = datetime.now(UTC) - timedelta(minutes=10)
        assert await redis_blob_storage.delete_stale(["a"], older_than=earlier) == 0
        assert await redis_blob_storage.get("a") is not None

    async def test_deletes_blobs_that_were_never_marked(self, redis_blob_storage: RedisBlobStorage):
        """Blobs written before the marker existed carry none."""
        await redis_blob_storage.client.set(BLOB_PREFIX + "a", b"text/plain\n1")

        assert await redis_blob_storage.delete_stale(["a"], older_than=datetime.now(UTC) - timedelta(hours=1)) == 1

    async def test_write_markers_expire(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))

        keys = [key async for key in redis_blob_storage.client.scan_iter()]
        ttls = [await redis_blob_storage.client.ttl(key) for key in keys if key != (BLOB_PREFIX + "a").encode()]
        assert len(ttls) == 1 and 0 < ttls[0] <= int(ORPHAN_GRACE.total_seconds())


class TestSharedRedis:
    """HARP shares its Redis database with other applications: it only ever touches its own keys."""

    async def test_iter_blob_ids_ignores_foreign_keys(self, redis_blob_storage: RedisBlobStorage):
        client = redis_blob_storage.client
        await client.set("session:alice", "data")
        await client.hset("other:hash", "f", "v")
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))

        assert [blob_id async for blob_id in redis_blob_storage.iter_blob_ids()] == ["a"]

    async def test_iter_blobs_survives_a_foreign_hash(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.hset("other:hash", "f", "v")
        meta = Blob(id="m", data=b"entry", content_type="cache/meta")
        await redis_blob_storage.put(meta)

        assert [blob async for blob in redis_blob_storage.iter_blobs("cache/meta")] == [meta]

    async def test_delete_stale_leaves_foreign_keys(self, redis_blob_storage: RedisBlobStorage):
        client = redis_blob_storage.client
        await client.set("session:alice", "data")
        await redis_blob_storage.put(Blob(id="a", data=b"1", content_type="text/plain"))

        ids = [blob_id async for blob_id in redis_blob_storage.iter_blob_ids()]
        await redis_blob_storage.delete_stale(ids, older_than=datetime.now(UTC) + timedelta(seconds=1))

        assert await client.get("session:alice") == b"data"
        assert await redis_blob_storage.get("a") is None


LEGACY_ID = "a" * 40


class TestLegacyUnprefixedBlobs:
    """Blobs written before the prefix existed sit under their bare id."""

    async def test_are_still_read(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.set(LEGACY_ID, b"text/plain\nbar")

        assert await redis_blob_storage.exists(LEGACY_ID)
        assert await redis_blob_storage.get(LEGACY_ID) == Blob(id=LEGACY_ID, data=b"bar", content_type="text/plain")

    async def test_are_deleted_with_their_id(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.set(LEGACY_ID, b"text/plain\nbar")

        await redis_blob_storage.delete(LEGACY_ID)

        assert not await redis_blob_storage.exists(LEGACY_ID)

    async def test_are_never_listed(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.set(LEGACY_ID, b"text/plain\nbar")

        assert [blob_id async for blob_id in redis_blob_storage.iter_blob_ids()] == []

    @pytest.mark.parametrize("key", ["session:alice", "old", "A" * 40, "a" * 39])
    async def test_foreign_keys_are_not_blobs(self, redis_blob_storage: RedisBlobStorage, key: str):
        await redis_blob_storage.client.set(key, b"text/plain\nsecret")

        assert await redis_blob_storage.get(key) is None
        assert not await redis_blob_storage.exists(key)

    async def test_non_string_foreign_key_is_not_a_blob(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.lpush("queue:jobs", b"x")

        assert await redis_blob_storage.get("queue:jobs") is None

    async def test_foreign_key_is_not_deleted(self, redis_blob_storage: RedisBlobStorage):
        await redis_blob_storage.client.set("session:alice", b"data")

        await redis_blob_storage.delete("session:alice")

        assert await redis_blob_storage.client.get("session:alice") == b"data"

    async def test_http_cache_entries_of_0_12_are_still_read(self, redis_blob_storage: RedisBlobStorage):
        key = "b" * 64
        await redis_blob_storage.client.set(key, b"cache/meta\nentry")

        assert await redis_blob_storage.get(key) == Blob(id=key, data=b"entry", content_type="cache/meta")

    @pytest.mark.parametrize("length", [40, 64])
    async def test_hex_named_list_key_is_not_a_blob(self, redis_blob_storage: RedisBlobStorage, length: int):
        key = "c" * length
        await redis_blob_storage.client.lpush(key, b"x")

        assert await redis_blob_storage.get(key) is None

    @pytest.mark.parametrize("length", [40, 64])
    async def test_hex_named_string_without_newline_is_not_a_blob(
        self, redis_blob_storage: RedisBlobStorage, length: int
    ):
        key = "d" * length
        await redis_blob_storage.client.set(key, b"no newline")

        assert await redis_blob_storage.get(key) is None
