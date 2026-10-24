import importlib.util
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, ConfigDict, UrlConstraints
from pydantic_core import MultiHostUrl
from sqlalchemy import URL

from harp.config import Configurable

ALLOWED_SCHEMES = [
    "mysql",
    "mysql+aiomysql",
    "postgresql",
    "postgresql+asyncpg",
    "sqlite",
    "sqlite+aiosqlite",
]


def _unwrap_sqlalchemy_urls(url):
    if isinstance(url, URL):
        return url.render_as_string(hide_password=False)
    return url


def _refuse_asyncmy(url):
    if str(url).startswith("mysql+asyncmy:"):
        raise ValueError("asyncmy is not supported anymore, use mysql+aiomysql:// instead")
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


# Driver module and the extra that installs it, for the backends not in the base install.
_DRIVER_EXTRAS = {
    "mysql+aiomysql": ("aiomysql", "mysql"),
    "postgresql+asyncpg": ("asyncpg", "postgresql"),
}


def _require_driver(url: MultiHostUrl) -> MultiHostUrl:
    module, extra = _DRIVER_EXTRAS.get(url.scheme, (None, None))
    if module and importlib.util.find_spec(module) is None:
        raise ValueError(
            f"{url.scheme} needs the {module} driver, which is not installed: pip install harp-proxy[{extra}]"
        )
    return url


DatabaseUrl = Annotated[
    MultiHostUrl,
    UrlConstraints(allowed_schemes=ALLOWED_SCHEMES),
    BeforeValidator(_refuse_asyncmy),
    BeforeValidator(_unwrap_sqlalchemy_urls),
    AfterValidator(_fix_unasync_dsns),
    AfterValidator(_require_driver),
]


class DatabaseSettings(Configurable):
    # validation errors must not echo the url: it carries the database password
    model_config = ConfigDict(hide_input_in_errors=True)

    url: DatabaseUrl = DatabaseUrl("sqlite+aiosqlite:///:memory:?cache=shared")
