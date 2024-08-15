import pytest

import harp
from harp.config import asdict
from harp.config.examples import (
    _get_available_documentation_examples_filenames,
    get_available_examples,
    get_example_filename,
)
from harp.utils.config import yaml


def test_get_available_examples(snapshot):
    assert get_available_examples() == snapshot


def test_documentation_examples_list(snapshot):
    assert [
        x.removeprefix(
            harp.ROOT_DIR + "/",
        )
        for x in _get_available_documentation_examples_filenames()
    ] == snapshot


@pytest.mark.parametrize("example", get_available_examples())
def test_load_example(example, snapshot):
    from harp.config import ConfigurationBuilder

    builder = ConfigurationBuilder()
    builder.add_file(get_example_filename(example))
    settings = builder.build()
    assert yaml.dump(asdict(settings)) == snapshot


@pytest.mark.parametrize("configfile", _get_available_documentation_examples_filenames())
def test_load_documentation_example(configfile, snapshot):
    from harp.config import ConfigurationBuilder

    builder = ConfigurationBuilder()
    if "/apps/rules/" in configfile:
        builder.applications.add("rules")
    builder.add_file(configfile)
    settings = builder.build()
    applications = settings.pop("applications", [])
    assert len(set(settings.keys()).difference(set(builder.applications.keys()))) == 0
    assert len(applications) >= len(settings)
    assert yaml.dump(asdict(settings)) == snapshot
