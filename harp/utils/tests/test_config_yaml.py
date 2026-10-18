import subprocess
import sys

import pytest
import yaml as pyyaml

import harp.services.references  # noqa: F401 (registers !ref/!cfg)
from harp.services.references import LazyServiceReference, LazySettingReference
from harp.utils.config import yaml
from harp.utils.config.yaml import YAMLFile

HARP_TAGS = ("!include", "!ref", "!cfg")


def test_import_harp_leaves_pyyaml_safe_loader_untouched():
    code = (
        "import yaml, harp, harp.services.references, harp.config.builders.configuration;"
        "print([t for t in ('!include', '!ref', '!cfg') if t in yaml.SafeLoader.yaml_constructors])"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


@pytest.mark.parametrize("loader", [pyyaml.SafeLoader, pyyaml.Loader, pyyaml.FullLoader])
def test_global_pyyaml_loaders_have_no_harp_tags(loader):
    for tag in HARP_TAGS:
        assert tag not in loader.yaml_constructors


def test_ref_and_cfg_tags(tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("a: !ref foo\nb: !cfg bar\n")
    data = yaml.load(str(f))
    assert isinstance(data["a"], LazyServiceReference)
    assert isinstance(data["b"], LazySettingReference)


def test_include_tag(tmp_path):
    (tmp_path / "inc.yml").write_text("x: 1\n")
    f = tmp_path / "a.yml"
    f.write_text(f"a: !include {tmp_path}/inc.yml\n")
    assert yaml.load(str(f)) == {"a": {"x": 1}}


def test_included_file_uses_safe_loader(tmp_path):
    (tmp_path / "evil.yml").write_text("x: !!python/object/apply:os.getcwd []\n")
    f = tmp_path / "a.yml"
    f.write_text(f"a: !include {tmp_path}/evil.yml\n")
    with pytest.raises(pyyaml.YAMLError):
        yaml.load(str(f))


def test_config_source_supports_harp_tags(tmp_path):
    (tmp_path / "inc.yml").write_text("x: 1\n")
    f = tmp_path / "a.yml"
    f.write_text(f"a: !include {tmp_path}/inc.yml\nb: !ref foo\n")
    data = YAMLFile(str(f)).read_source()
    assert data["a"] == {"x": 1}
    assert isinstance(data["b"], LazyServiceReference)
