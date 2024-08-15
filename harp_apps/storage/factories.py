from redis.asyncio import Redis

from harp.utils.services import factory
from harp_apps.storage.settings import StorageSettings


@factory(Redis)
def RedisClientFactory(self, settings: StorageSettings) -> Redis:
    return Redis.from_url(str(settings.blobs.url))
