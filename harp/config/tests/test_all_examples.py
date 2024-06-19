import pytest

from harp import Config
from harp.config.examples import get_available_examples


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


@pytest.mark.parametrize("example", get_available_examples())
def test_load_example(example):
    from harp.config.builder import ConfigurationBuilder

    builder = ConfigurationBuilder()
    builder.add_examples([example])
    settings = builder.build().values

    config = Config(settings)
    config.add_defaults()
    assert config.validate()
