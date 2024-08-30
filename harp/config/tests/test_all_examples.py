import os.path
from glob import glob
from itertools import chain

import pytest

import harp
from harp.config.asdict import asdict
from harp.config.examples import get_available_examples, get_example_filename
from harp.utils.config import yaml


def _get_available_documentation_examples_filenames():
    files = chain(
        *(
            glob(f"docs/**/examples/*.{format}", root_dir=harp.ROOT_DIR, recursive=True)
            for format in ("yml", "yaml", "toml")
        )
    )

    return list(sorted(files))


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
    settings = builder()
    assert yaml.dump(asdict(settings)) == snapshot


@pytest.mark.parametrize("configfile", _get_available_documentation_examples_filenames())
def test_load_documentation_example(configfile, snapshot):
    from harp.config import ConfigurationBuilder

    builder = ConfigurationBuilder()
    if configfile.startswith("docs/apps/rules/"):
        builder.applications.add("rules")
    builder.add_file(os.path.join(harp.ROOT_DIR, configfile))
    settings = builder()
    applications = settings.pop("applications", [])
    assert len(set(settings.keys()).difference(set(builder.applications.keys()))) == 0
    assert len(applications) >= len(settings)
    assert yaml.dump(asdict(settings)) == snapshot
