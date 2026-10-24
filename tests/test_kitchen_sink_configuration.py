"""Keep every kitchen-sink run mode's example configuration loadable."""

from pathlib import Path

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "misc" / "kitchen-sink" / "etc"


@pytest.mark.parametrize("path", sorted(CONFIG_DIR.glob("*.yml")), ids=lambda path: path.name)
def test_kitchen_sink_configuration_is_valid_yaml(path):
    assert isinstance(yaml.safe_load(path.read_text()), dict)
