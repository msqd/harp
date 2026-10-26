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
    assert _loaded(files=[f]) == {"storage", "proxy", "http_client"}


def test_no_list_keeps_defaults(tmp_path):
    f = _write(tmp_path, "a.yml", "storage: {}\n")
    assert "dashboard" in _loaded(files=[f])


def test_unknown_application_fails_naming_it(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, nope_app]\n")
    with pytest.raises(ModuleNotFoundError, match="nope_app"):
        _loaded(files=[f])


def test_cli_applications_replace_file_list(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert _loaded(files=[f], applications=["janitor"]) == {"janitor"}


def test_enable_disable_apply_after_file_list(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert _loaded(files=[f], enable=["http_client"], disable=["janitor"]) == {"storage", "proxy", "http_client"}


def test_last_file_list_wins(tmp_path):
    a = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    b = _write(tmp_path, "b.yml", "applications: [http_client]\n")
    c = _write(tmp_path, "c.yml", "storage: {}\n")
    assert _loaded(files=[a, b, c]) == {"http_client"}


def test_a_list_gains_the_dependencies_of_its_applications(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage]\n")
    assert _loaded(files=[f]) == {"storage", "proxy", "http_client"}


def test_dashboard_pulls_auth_in_whatever_the_list(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [dashboard]\n")
    assert {"dashboard", "auth", "storage", "proxy"} <= _loaded(files=[f])


def test_default_set_loads_auth_before_the_dashboard_that_needs_it():
    builder = ConfigurationBuilder.from_commandline_options(_options())
    builder.build()
    names = list(builder.applications)
    assert names.index("storage") < names.index("auth") < names.index("dashboard")


def test_without_dashboard_no_auth_is_loaded(tmp_path):
    f = _write(tmp_path, "a.yml", "applications: [storage, proxy]\n")
    assert "auth" not in _loaded(files=[f])
    assert "auth" not in _loaded(disable=["dashboard"])


def test_disabling_a_dependency_still_fails_naming_it():
    from harp.errors import MissingDependencyError

    builder = ConfigurationBuilder.from_commandline_options(_options(disable=["proxy"]))
    with pytest.raises(MissingDependencyError, match=r"requires 'proxy'"):
        builder.applications.validate_dependencies()
