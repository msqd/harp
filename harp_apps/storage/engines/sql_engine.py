from pydantic_core import MultiHostUrl
from sqlalchemy import StaticPool, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class SQLAlchemyEngine(AsyncEngine):
    @staticmethod
    def from_url(url: MultiHostUrl) -> AsyncEngine:
        database_url = make_url(str(url))
        if database_url.get_dialect() == "sqlite" and database_url.database == ":memory:":
            return create_async_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )

        return create_async_engine(database_url)
