import functools
import itertools

import pytest

from harp.utils.env import get_bool_from_env

# Setting to chose whether to test an extensive set of underlying database systems or a representing subset. Generally,
# unless you are testing a complex feature or running a final barier continuous nintegration system, the subset should
# be enough (and faster).
TEST_ALL_DATABASES = get_bool_from_env("TEST_ALL_DATABASES", False)

# Supported databases, containers and their drivers. This will be used as a matrix to parametrize tests.
TEST_DATABASES_SOURCES = {
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
                ]
            ),
        ],
        "drivers": ["asyncpg"],
    },
    "mysql": {
        "images": (
            [
                "mysql:8-oracle",
                "mariadb:lts",
                "mariadb:latest",
            ]
            if TEST_ALL_DATABASES
            else ["mariadb:lts"]
        ),
        "drivers": ["aiomysql", "asyncmy"] if TEST_ALL_DATABASES else ["aiomysql"],
    },
    # disabled, does not install cleanly on osx+arm
    # see https://github.com/pymssql/pymssql/issues/769
    # supporting microsoft shit is not a priority unless someone wants to sponsor it
    # "mssql": {"drivers": ["aioodbc"]},
}

# Combine supported databases into something our fixtures can use.
TEST_DATABASES = list(
    map(
        "|".join,
        itertools.chain(
            *(
                itertools.product(
                    [dialect],
                    TEST_DATABASES_SOURCES[dialect].get("images", [""]),
                    TEST_DATABASES_SOURCES[dialect]["drivers"],
                )
                for dialect in TEST_DATABASES_SOURCES.keys()
            )
        ),
    )
)


def parametrize_with_database_urls(*databases):
    """
    Decorator to parametrize with all supported databases (no parameters) or a subset of supported databases.

    Usage::

    @parametrize_with_database_urls():
    def test_all_databases(database_url):
        ... # will receive all supported databases urls, while a matching container runs

    @parametrize_with_database_urls("postgresql", "mysql")
    def test_all_databases(database_url):
        ... # will receive supported databases urls matching parameters, while a matching container runs
    """

    def wrapper(func):
        @pytest.mark.parametrize(
            "database_url",
            (
                [x for x in TEST_DATABASES if any(x.startswith(db + "|") for db in databases)]
                if len(databases)
                else TEST_DATABASES
            ),
            indirect=True,
        )
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            return await func(*args, **kwargs)

        return inner

    return wrapper
