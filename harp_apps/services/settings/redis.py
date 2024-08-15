from pydantic import RedisDsn

from harp.config import Configurable


class RedisSettings(Configurable):
    url: RedisDsn = RedisDsn("redis://localhost:6379/0")
