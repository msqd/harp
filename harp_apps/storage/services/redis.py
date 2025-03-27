from typing import Optional

from redis.asyncio import Redis as BaseRedis


class Redis(BaseRedis):
    @classmethod
    def from_url(
        cls, url, single_connection_client: bool = False, auto_close_connection_pool: Optional[bool] = None, **kwargs
    ):
        return super().from_url(
            str(url),
            single_connection_client=single_connection_client,
            auto_close_connection_pool=auto_close_connection_pool,
            **kwargs,
        )
