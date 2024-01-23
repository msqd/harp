import asyncio
import itertools
from typing import Iterator
from unittest.mock import patch

import pytest
from pytest import FixtureRequest

from harp.utils.network import wait_for_port


@pytest.fixture(scope="session", autouse=True)
def default_session_fixture():
    from harp.config import Config

    DEFAULT_APPLICATIONS_FOR_TESTS = list(Config.DEFAULT_APPLICATIONS)
    DEFAULT_APPLICATIONS_FOR_TESTS.remove("harp_apps.telemetry")

    with patch("harp.config.Config.DEFAULT_APPLICATIONS", DEFAULT_APPLICATIONS_FOR_TESTS):
        yield


# see https://github.com/GrahamDumpleton/wrapt/issues/257
@pytest.fixture(autouse=True, scope="session")
def patch_wrapt_for_pycharm():
    from wrapt import FunctionWrapper, decorators
    from wrapt.decorators import AdapterWrapper, _AdapterFunctionSurrogate

    class _PatchedAdapterFunctionSurrogate(_AdapterFunctionSurrogate):
        @property
        def __class__(self):
            try:
                return super().__class__
            except ValueError:
                return type(self)

    class PatchedAdapterWrapper(AdapterWrapper):
        def __init__(self, *args, **kwargs):
            adapter = kwargs.pop("adapter")
            FunctionWrapper.__init__(self, *args, **kwargs)
            self._self_surrogate = _PatchedAdapterFunctionSurrogate(self.__wrapped__, adapter)
            self._self_adapter = adapter

        @property
        def __class__(self):
            try:
                return super().__class__
            except ValueError:
                return type(self)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(decorators, "AdapterWrapper", PatchedAdapterWrapper)
        yield


# redefine event loop fixture with a broad scope.
# see https://pytest-asyncio.readthedocs.io/en/latest/reference/decorators/index.html
# this is mostly to avoid to create one container per integration test, we'll reuse the third party services running in
# docker from one test to another
@pytest.fixture(scope="session")
def event_loop(request: FixtureRequest) -> Iterator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def get_bool_from_env(key, default):
    import os

    value = os.environ.get(key, None)
    if value is None:
        return default
    elif value.lower() in ("true", "1", "yes"):
        return True
    elif value.lower() in ("false", "0", "no"):
        return False
    else:
        raise ValueError(f"Invalid boolean value for {key}: {value!r}")


TEST_ALL_DATABASES = get_bool_from_env("TEST_ALL_DATABASES", False)

DBS = {
    "sqlite": {"drivers": ["aiosqlite"]},
    "postgresql": {
        "images": [
            *(
                [
                    "postgres:12",
                    "postgres:12-alpine",
                    "postgres:13",
                    "postgres:13-alpine",
                    "postgres:14",
                    "postgres:14-alpine",
                    "postgres:15",
                    "postgres:15-alpine",
                    "postgres:16",
                    "postgres:16-alpine",
                    "timescale/timescaledb:latest-pg13",
                    "timescale/timescaledb:latest-pg14",
                    "timescale/timescaledb:latest-pg15",
                    "timescale/timescaledb:latest-pg16",
                ]
                if TEST_ALL_DATABASES
                else [
                    "postgres:16-alpine",
                    "timescale/timescaledb:latest-pg16",
                ]
            ),
        ],
        "drivers": ["asyncpg"],
    },
    "mysql": {
        "images": [
            "mysql:8-oracle",
            "mariadb:lts",
            "mariadb:latest",
        ]
        if TEST_ALL_DATABASES
        else ["mariadb:lts"],
        "drivers": ["aiomysql", "asyncmy"],
    },
    # disabled, does not install cleanly on osx+arm
    # see https://github.com/pymssql/pymssql/issues/769
    # supporting microsoft shit is not a priority unless someone wants to sponsor it
    # "mssql": {"drivers": ["aioodbc"]},
}

DATABASES = list(
    map(
        "|".join,
        itertools.chain(
            *(
                itertools.product(
                    [dialect],
                    DBS[dialect].get("images", [""]),
                    DBS[dialect]["drivers"],
                )
                for dialect in DBS.keys()
            )
        ),
    )
)


@pytest.fixture(
    scope="session",
    params=DATABASES,
)
def database_url(request):
    dialect, image, driver = request.param.split("|")
    if dialect == "sqlite":
        yield f"{dialect}+{driver}:///:memory:"
    elif dialect == "postgresql":
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer(image) as container:
            yield container.get_connection_url().replace("postgresql+psycopg2://", f"{dialect}+{driver}://")
    elif dialect == "mysql":
        from testcontainers.mysql import MySqlContainer

        with MySqlContainer(image) as container:
            yield container.get_connection_url().replace("mysql+pymysql://", f"{dialect}+{driver}://")
    elif dialect == "mssql":
        from testcontainers.mssql import SqlServerContainer

        with SqlServerContainer() as container:
            yield container.get_connection_url().replace("mssql+pymssql://", f"{dialect}+{driver}://")
    else:
        raise ValueError(f"Unsupported or invalid dialect: {dialect!r}")


@pytest.fixture(scope="session")
def httpbin():
    from testcontainers.core.container import DockerContainer

    with DockerContainer("mccutchen/go-httpbin:v2.13.2").with_exposed_ports(8080) as container:
        wait_for_port(int(container.get_exposed_port(8080)))
        yield f"http://localhost:{container.get_exposed_port(8080)}"
