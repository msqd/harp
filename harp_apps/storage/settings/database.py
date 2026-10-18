import importlib.util
import re
from typing import Annotated
from urllib.parse import parse_qs, urlsplit

from pydantic import AfterValidator, BeforeValidator, UrlConstraints
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


_EMPTY_HOST = re.compile(r"^([\w+]+://[^/@]+@)(?=/)")


def _name_socket_hosts(url):
    """
    Gives a placeholder host to ``scheme://user@/db?host=/socket/dir``: the url parser refuses credentials with an
    empty host, but the ``host`` query parameter overrides it in SQLAlchemy and the drivers.
    """
    if isinstance(url, str) and "host" in parse_qs(urlsplit(url).query):
        return _EMPTY_HOST.sub(r"\1localhost", url)
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
    BeforeValidator(_name_socket_hosts),
    BeforeValidator(_unwrap_sqlalchemy_urls),
    AfterValidator(_fix_unasync_dsns),
    AfterValidator(_require_driver),
]


class DatabaseSettings(Configurable):
    url: DatabaseUrl = DatabaseUrl("sqlite+aiosqlite:///:memory:?cache=shared")
