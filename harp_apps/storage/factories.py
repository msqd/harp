from redis.asyncio import Redis

from harp.utils.services import factory
from harp_apps.storage.settings import StorageSettings


@factory(Redis)
def RedisClientFactory(self, settings: StorageSettings) -> Redis:
    return Redis.from_url(settings.blobs.url.render_as_string(hide_password=False))
