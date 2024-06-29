from contextlib import asynccontextmanager


@asynccontextmanager
async def create_redis_client():
    from testcontainers.redis import AsyncRedisContainer

    with AsyncRedisContainer() as redis_container:
        yield await redis_container.get_async_client()
