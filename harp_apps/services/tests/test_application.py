from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from harp.config import ConfigurationBuilder, SystemBuilder


async def test_lifecycle_redis():
    config = ConfigurationBuilder(
        {
            "applications": ["services"],
            "services": {
                "redis": {
                    "url": "redis://localhost:6379/0",
                }
            },
        },
        use_default_applications=False,
    )
    system = await SystemBuilder(config).abuild()

    redis = system.provider.get("redis")
    assert isinstance(redis, Redis)


async def test_lifecycle_sqlalchemy():
    config = ConfigurationBuilder(
        {
            "applications": ["services"],
            "services": {
                "database": {
                    "url": "postgresql://user:pass@localhost:5432/harp",
                },
            },
        },
        use_default_applications=False,
    )
    system = await SystemBuilder(config).abuild()

    engine = system.provider.get("database")
    assert isinstance(engine, AsyncEngine)
