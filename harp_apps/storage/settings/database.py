from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, UrlConstraints
from pydantic_core import MultiHostUrl
from sqlalchemy import URL

from harp.config import Configurable

ALLOWED_SCHEMES = [
    "mysql",
    "mysql+aiomysql",
    "mysql+asyncmy",
    "postgresql",
    "postgresql+asyncpg",
    "sqlite",
    "sqlite+aiosqlite",
]


def _unwrap_sqlalchemy_urls(url):
    if isinstance(url, URL):
        return url.render_as_string(hide_password=False)
    return url


def _fix_unasync_dsns(url: str | MultiHostUrl) -> MultiHostUrl:
    if isinstance(url, MultiHostUrl):
        url = str(url)
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+aiomysql://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://")
    return MultiHostUrl(url)


DatabaseUrl = Annotated[
    MultiHostUrl,
    UrlConstraints(host_required=True, allowed_schemes=ALLOWED_SCHEMES),
    BeforeValidator(_unwrap_sqlalchemy_urls),
    AfterValidator(_fix_unasync_dsns),
]


class DatabaseSettings(Configurable):
    url: DatabaseUrl = DatabaseUrl("sqlite+aiosqlite:///:memory:?cache=shared")
