"""Tests for the example ``config.yml`` generator (source-introspected reference config)."""

import yaml

from harp.config.builders.configuration import ConfigurationBuilder
from harp.config.example import iter_app_settings, render_example_config


class TestIterAppSettings:
    def test_includes_default_apps_that_have_settings(self):
        names = dict(iter_app_settings())
        assert {"dashboard", "storage", "proxy", "http_client", "http_cache"} <= set(names)

    def test_skips_apps_without_a_settings_model(self):
        # janitor is a default application but declares no settings model.
        assert "janitor" not in dict(iter_app_settings())

    def test_each_app_block_is_serialisable_and_valid_yaml(self):
        for name, settings in iter_app_settings():
            dumped = yaml.safe_dump({name: settings}, sort_keys=False)
            assert yaml.safe_load(dumped) == {name: settings}


class TestRenderExampleConfig:
    def test_returns_a_string(self):
        assert isinstance(render_example_config(), str)

    def test_is_fully_commented_out(self):
        # The whole file is a reference: dropping it into a project must not activate any
        # configuration, so every non-blank line has to be a comment.
        for line in render_example_config().splitlines():
            assert line == "" or line.startswith("#"), f"unexpected active line: {line!r}"

    def test_contains_a_commented_block_of_valid_yaml_for_each_app(self):
        text = render_example_config()
        for name, settings in iter_app_settings():
            dumped = yaml.safe_dump({name: settings}, sort_keys=False)
            assert yaml.safe_load(dumped) is not None
            for line in dumped.splitlines():
                assert f"# {line}" in text, f"missing commented line for {name}: {line!r}"

    def test_has_a_documentation_url_per_app(self):
        text = render_example_config()
        for name, _ in iter_app_settings():
            assert f"https://docs.harp-project.net/en/latest/apps/{name}/" in text

    def test_uses_the_current_documentation_domain(self):
        # The documentation moved to docs.harp-project.net; the generated reference must not
        # point users at the retired docs.harp-proxy.net domain.
        text = render_example_config()
        assert "docs.harp-proxy.net" not in text
        assert "https://docs.harp-project.net/" in text


class TestGeneratedConfigIsLoadable:
    def test_fully_commented_config_loads_as_an_empty_configuration(self, tmp_path):
        # A scaffolded project ships a comments-only config.yml; harp must still be able to
        # load it (it parses to nothing) and start on defaults.
        path = tmp_path / "config.yml"
        path.write_text(render_example_config())
        builder = ConfigurationBuilder(use_default_applications=True)
        builder.add_file(str(path))
        builder.build()  # must not raise

    def test_empty_config_file_loads(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("\n")
        builder = ConfigurationBuilder(use_default_applications=True)
        builder.add_file(str(path))
        builder.build()  # must not raise
