"""Each configuration source is parsed once per build (see #1566)."""

from harp.config.builders import ConfigurationBuilder
from harp.config.builders import configuration as builders_configuration
from harp.utils.config.yaml import YAMLFile


def _count_reads(monkeypatch):
    reads = []
    original = YAMLFile.read_source

    def read_source(self):
        reads.append(str(self.file_path))
        return original(self)

    monkeypatch.setattr(YAMLFile, "read_source", read_source)
    return reads


def test_added_file_is_parsed_once_per_build(tmp_path, monkeypatch):
    path = tmp_path / "a.yml"
    path.write_text("applications: [storage, proxy]\nstorage: {}\n")
    reads = _count_reads(monkeypatch)

    builder = ConfigurationBuilder()
    builder.add_file(str(path))
    builder.build()

    assert reads == [str(path)]


def test_system_file_is_parsed_once_per_build(tmp_path, monkeypatch):
    path = tmp_path / "harp.yml"
    path.write_text("applications: [storage, proxy]\n")
    monkeypatch.setattr(builders_configuration, "DEFAULT_SYSTEM_CONFIG_FILENAMES", [str(path)])
    reads = _count_reads(monkeypatch)

    builder = ConfigurationBuilder()
    builder.build()

    assert reads == [str(path)]
