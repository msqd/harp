"""Every documented configuration that sets `applications:` must start (see #1216)."""

import re
from glob import glob
from types import SimpleNamespace

import pytest

import harp
from harp.config.builders import ConfigurationBuilder

_YAML_BLOCK = re.compile(
    r"^(?P<indent> *)\.\. (?:code-block|code):: yaml\n(?:\s*:\w+:.*\n)*\n(?P<body>(?:(?P=indent) +.*\n|\n)+)", re.M
)


def _documented_configurations():
    for filename in sorted(glob("docs/**/*.rst", root_dir=harp.ROOT_DIR, recursive=True)):
        if filename.startswith("docs/changelogs/"):
            continue
        with open(f"{harp.ROOT_DIR}/{filename}") as f:
            content = f.read()
        for i, match in enumerate(_YAML_BLOCK.finditer(content)):
            lines = match.group("body").splitlines()
            indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
            body = "\n".join(line[indent:] for line in lines) + "\n"
            if re.search(r"^applications:", body, re.M):
                yield pytest.param(body, id=f"{filename}#{i}")


def test_documented_configurations_are_found():
    assert len(list(_documented_configurations())) >= 2


@pytest.mark.parametrize(
    "body", [p.values[0] for p in _documented_configurations()], ids=[p.id for p in _documented_configurations()]
)
def test_documented_applications_start(tmp_path, body):
    path = tmp_path / "config.yml"
    path.write_text(body)
    options = SimpleNamespace(
        applications=None, enable=(), disable=(), examples=(), files=[str(path)], options={}, endpoints={}, strict=False
    )
    builder = ConfigurationBuilder.from_commandline_options(options)
    builder.build()
    builder.applications.resolve_dependencies()
