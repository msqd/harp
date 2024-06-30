import pytest

import harp
from harp import Config
from harp.config.examples import _get_available_documentation_examples_filenames, get_available_examples


def test_examples_list():
    assert get_available_examples() == [
        "auth.basic",
        "httpbin",
        "httpbins",
        "postgres",
        "repositories",
        "sentry",
        "sqlite",
    ]


def test_documentation_examples_list():
    assert [x.removeprefix(harp.ROOT_DIR + "/") for x in _get_available_documentation_examples_filenames()] == [
        "docs/apps/dashboard/examples/auth.basic.yml",
        "docs/apps/dashboard/examples/auth.yml",
        "docs/apps/dashboard/examples/devserver.yml",
        "docs/apps/dashboard/examples/main.yml",
        "docs/apps/http_client/examples/full.yml",
        "docs/apps/http_client/examples/simple.yml",
        "docs/apps/proxy/examples/swapi.yml",
        "docs/apps/storage/examples/mysql-aiomysql.yml",
        "docs/apps/storage/examples/mysql-asyncmy.yml",
        "docs/apps/storage/examples/postgres-asyncpg.yml",
        "docs/apps/storage/examples/redis.yml",
        "docs/apps/storage/examples/sqlite-aiosqlite.yml",
    ]


@pytest.mark.parametrize("example", get_available_examples())
def test_load_example(example):
    from harp.config.builder import ConfigurationBuilder

    builder = ConfigurationBuilder()
    builder.add_examples([example])
    settings = builder.build().values

    config = Config(settings)
    config.add_defaults()
    assert config.validate()


@pytest.mark.parametrize("configfile", _get_available_documentation_examples_filenames())
def test_load_documentation_example(configfile):
    from harp.config.builder import ConfigurationBuilder

    builder = ConfigurationBuilder()
    builder.add_files([configfile])
    settings = builder.build().values

    config = Config(settings)
    config.add_defaults()
    assert config.validate()
