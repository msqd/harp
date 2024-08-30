from pydantic import RedisDsn

from harp.config import Service


class RedisSettings(Service):
    url: RedisDsn = RedisDsn("redis://localhost:6379/0")
