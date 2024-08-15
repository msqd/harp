from typing import cast

from rodi import Container

from harp.utils.services import factory
from harp_apps.services.settings import RedisSettings


def register_redis_service(container: Container, settings: RedisSettings):
    from redis.asyncio import Redis

    redis_dsn = str(settings.url)

    @factory(Redis)
    def RedisFactory(self) -> Redis:
        nonlocal redis_dsn
        return Redis.from_url(redis_dsn)

    container.add_singleton(Redis, cast(type, RedisFactory))
    container.set_alias("redis", Redis)
