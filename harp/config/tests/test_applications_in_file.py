"""`applications:` in a configuration file replaces the default set (see #994)."""

from types import SimpleNamespace

import pytest

from harp.config.builders import ConfigurationBuilder


def _options(files=(), **kwargs):
    defaults = dict(
        applications=None, enable=(), disable=(), examples=(), files=files, options={}, endpoints={}, strict=False
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def _loaded(**kwargs):
    builder = ConfigurationBuilder.from_commandline_options(_options(**kwargs))
    builder.build()
    return set(builder.applications.keys())


def test_file_list_replaces_defaults(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert _loaded(files=[f]) == {"storage", "proxy"}


def test_no_list_keeps_defaults(tmp_path):
    f = _write(tmp_path, "a.yml", "storage: {}\n")
    assert "dashboard" in _loaded(files=[f])


def test_unknown_application_fails_naming_it(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, nope_app]\n")
    with pytest.raises(ModuleNotFoundError, match="nope_app"):
        _loaded(files=[f])


def test_cli_applications_replace_file_list(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert _loaded(files=[f], applications=["storage"]) == {"storage"}


def test_enable_disable_apply_after_file_list(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert _loaded(files=[f], enable=["http_client"], disable=["proxy"]) == {"storage", "http_client"}


def test_last_file_list_wins(tmp_path):
    a = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    b = _write(tmp_path, "b.yml", "applications: [storage]\n")
    c = _write(tmp_path, "c.yml", "storage: {}\n")
    assert _loaded(files=[a, b, c]) == {"storage"}


def test_incomplete_list_error_names_missing_application_and_fix(tmp_path):
    from harp.errors import MissingDependencyError

    f = _write(tmp_path, "a.yml", "applications: [storage]\n")
    builder = ConfigurationBuilder.from_commandline_options(_options(files=[f]))
    with pytest.raises(MissingDependencyError, match=r"requires 'proxy'.*Add it to the 'applications' list"):
        builder.applications.resolve_dependencies()
