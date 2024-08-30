from contextlib import asynccontextmanager

from redis.asyncio import Redis


@asynccontextmanager
async def create_redis_client() -> Redis:
    from testcontainers.redis import AsyncRedisContainer

    with AsyncRedisContainer() as redis_container:
        client = await redis_container.get_async_client()
        try:
            yield client
        finally:
            await client.aclose()
