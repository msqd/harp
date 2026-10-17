"""Tests for the metadata recorded alongside benchmark results (see `bench/`)."""

import subprocess

from bench import metadata


class TestNative:
    def test_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("HARP_NATIVE", raising=False)
        assert metadata.native() == "none"

    def test_value_when_set(self, monkeypatch):
        monkeypatch.setenv("HARP_NATIVE", "blobs,hashing")
        assert metadata.native() == "blobs,hashing"


class TestCpuModel:
    def test_reads_model_name(self, tmp_path):
        cpuinfo = tmp_path / "cpuinfo"
        cpuinfo.write_text("processor\t: 0\nmodel name\t: Some CPU @ 3.00GHz\n")
        assert metadata.cpu_model(cpuinfo) == "Some CPU @ 3.00GHz"

    def test_unknown_when_unreadable(self, tmp_path):
        assert metadata.cpu_model(tmp_path / "missing") == "unknown"


class TestGitDirty:
    def _repo(self, path):
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        return path

    def test_false_on_clean_tree(self, tmp_path):
        assert metadata.git_dirty(self._repo(tmp_path)) == "false"

    def test_true_with_uncommitted_changes(self, tmp_path):
        (self._repo(tmp_path) / "file").write_text("x")
        assert metadata.git_dirty(tmp_path) == "true"

    def test_unknown_outside_a_repository(self, tmp_path):
        assert metadata.git_dirty(tmp_path / "missing") == "unknown"


class TestCollect:
    def test_has_all_keys(self):
        assert set(metadata.collect()) == {"git_sha", "git_dirty", "harp_native", "cpu_model", "python_build"}

    def test_values_are_strings(self):
        assert all(isinstance(value, str) and value for value in metadata.collect().values())
