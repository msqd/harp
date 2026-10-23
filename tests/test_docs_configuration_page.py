import re
from pathlib import Path

import pytest

from harp.config import ConfigurationBuilder

PAGE = Path(__file__).parent.parent / "docs" / "operate" / "configure" / "index.rst"
YAML_BLOCK = re.compile(r"^\.\. code-block:: yaml\n\n((?:(?: {4}.*)?\n)+)", re.MULTILINE)
BLOCKS = [
    "\n".join(line[4:] for line in match.group(1).splitlines()) + "\n"
    for match in YAML_BLOCK.finditer(PAGE.read_text())
]


def test_page_has_yaml_blocks():
    assert BLOCKS


def _builder(block, tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(block)
    builder = ConfigurationBuilder()
    builder.add_file(str(path))
    return builder


@pytest.mark.parametrize("block", BLOCKS, ids=lambda block: block.splitlines()[0])
def test_yaml_block_settings_are_valid(block, tmp_path):
    _builder(block, tmp_path).build()


@pytest.mark.parametrize("block", BLOCKS, ids=lambda block: block.splitlines()[0])
async def test_yaml_block_binds(block, tmp_path):
    builder = _builder(block, tmp_path)
    # the documented database may not exist here: bind against the in-memory one.
    builder.add_value("storage.url", "sqlite+aiosqlite:///:memory:?cache=shared")

    system = await builder.abuild_system()
    await system.dispose()
