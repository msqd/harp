import pytest
from redis.asyncio import Redis

from harp.config import ConfigurationBuilder
from harp.models import Blob
from harp.services import CannotResolveTypeException
from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage


async def test_basics(redis_blob_storage: RedisBlobStorage):
    _storage = redis_blob_storage
    assert _storage.client is not None
    blob = Blob(id="foo", data=b"bar", content_type="text/plain")

    assert _storage.type == "redis"
    assert await _storage.get("foo") is None
    assert await _storage.client.get("foo") is None

    assert await _storage.put(blob) == blob
    assert await _storage.get("foo") == blob
    assert await _storage.client.get("foo") == b"text/plain\nbar"

    assert await _storage.exists("foo")
    assert await _storage.delete("foo") is None
    assert not await _storage.exists("foo")
    assert await _storage.get("foo") is None
    assert await _storage.client.get("foo") is None


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
        ).abuild_system()
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
