from typing import Optional

from pydantic_core import Url
from redis.asyncio import Redis as BaseRedis


class Redis(BaseRedis):
    @classmethod
    def from_url(
        cls,
        url: str | Url,
        single_connection_client: bool = False,
        auto_close_connection_pool: Optional[bool] = None,
        **kwargs,
    ):
        if isinstance(url, Url):
            url = str(url)
        return super().from_url(
            url,
            single_connection_client=single_connection_client,
            auto_close_connection_pool=auto_close_connection_pool,
            **kwargs,
        )
