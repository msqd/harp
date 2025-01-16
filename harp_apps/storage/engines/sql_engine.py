from typing import Any, Union

from pydantic_core import MultiHostUrl
from sqlalchemy import URL, StaticPool, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine


def create_async_engine(url: Union[str, URL], **kw: Any) -> AsyncEngine:
    url = make_url(url)
    kw.setdefault("connect_args", {})

    if url.get_dialect() == "postgresql":
        kw["connect_args"].setdefault("server_settings", {})
        # This is necessary so that postgres always send back utc datetimes, we'll handle timezone specific logic
        # ourselves to avoid differences between environments. Override at your own risk.
        kw["connect_args"]["server_settings"].setdefault("timezone", "UTC")
    engine = _create_async_engine(url, **kw)
    return engine


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
