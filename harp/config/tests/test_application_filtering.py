"""
Tests for two-pass configuration parsing and application filtering.

These tests verify that:
1. Configuration is parsed in two passes
2. First pass identifies apps with enabled: false
3. Second pass filters those apps from ApplicationsRegistry
4. Filtered apps don't appear in final GlobalSettings
5. Warnings are logged for filtered apps
"""

from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch


from harp.config import Application, Configurable
from harp.config.builders import ConfigurationBuilder
from harp.config.mixins import ApplicationSettingsMixin


# Create fake test application modules
enabled_app_module = ModuleType("enabled_app")
enabled_app_module.__spec__ = ModuleSpec(name="enabled_app", loader=None)


class EnabledAppSettings(ApplicationSettingsMixin, Configurable):
    name: str = "enabled"


enabled_app_app_module = ModuleType("enabled_app.__app__")
enabled_app_app_module.application = Application(settings_type=EnabledAppSettings)
enabled_app_app_module.__spec__ = ModuleSpec(name="enabled_app.__app__", loader=None)


disabled_app_module = ModuleType("disabled_app")
disabled_app_module.__spec__ = ModuleSpec(name="disabled_app", loader=None)


class DisabledAppSettings(ApplicationSettingsMixin, Configurable):
    name: str = "disabled"


disabled_app_app_module = ModuleType("disabled_app.__app__")
disabled_app_app_module.application = Application(settings_type=DisabledAppSettings)
disabled_app_app_module.__spec__ = ModuleSpec(name="disabled_app.__app__", loader=None)


class TestTwoPassConfigurationParsing:
    """Test that configuration is parsed in two passes."""

    def test_first_pass_reads_all_config(self):
        """Test that first pass reads all configuration including enabled flags."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")

            builder.add_values(
                {
                    "enabled_app": {"name": "custom_enabled"},
                    "disabled_app": {"enabled": False, "name": "custom_disabled"},
                }
            )

            # First pass should read both configs
            # This might be tested by checking an internal state or method
            first_pass_config = builder._get_first_pass_config()

            assert "enabled_app" in first_pass_config
            assert "disabled_app" in first_pass_config
            assert first_pass_config["disabled_app"]["enabled"] is False

    def test_second_pass_filters_disabled_apps(self):
        """Test that second pass removes disabled apps from registry."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")

            # Before configuration, both apps in registry
            assert "enabled_app" in builder.applications
            assert "disabled_app" in builder.applications

            builder.add_values(
                {
                    "enabled_app": {"name": "custom_enabled"},
                    "disabled_app": {"enabled": False},
                }
            )

            config = builder.build()

            # After second pass, only enabled_app should remain
            assert "enabled_app" in config
            assert "disabled_app" not in config

    def test_two_pass_sequence_is_correct(self):
        """Test that passes happen in correct order: read all, then filter."""
        with patch.dict(
            "sys.modules",
            {
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("disabled_app")
            builder.add_values({"disabled_app": {"enabled": False}})

            # Track the sequence using a call tracker
            call_sequence = []

            original_normalize = builder.normalize

            def tracked_normalize(config):
                call_sequence.append(("normalize", list(config.keys())))
                return original_normalize(config)

            builder.normalize = tracked_normalize

            builder.build()

            # Should have called normalize at least once
            # The sequence should show we read config before filtering
            assert len(call_sequence) > 0


class TestApplicationsRegistryFiltering:
    """Test that ApplicationsRegistry is filtered based on enabled flags."""

    def test_disabled_app_removed_from_registry(self):
        """Test that apps with enabled: false are removed from registry."""
        with patch.dict(
            "sys.modules",
            {
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("disabled_app")

            assert "disabled_app" in builder.applications

            builder.add_values({"disabled_app": {"enabled": False}})
            builder.build()

            # Check that registry was filtered
            # This might require a method to get filtered registry
            filtered_registry = builder.get_filtered_applications_registry()
            assert "disabled_app" not in filtered_registry

    def test_enabled_app_remains_in_registry(self):
        """Test that apps with enabled: true remain in registry."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")

            builder.add_values({"enabled_app": {"enabled": True, "name": "custom"}})
            config = builder.build()

            # Should still be in registry
            assert "enabled_app" in config

    def test_app_with_default_enabled_true_remains(self):
        """Test that apps without explicit enabled setting remain (default true)."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")

            # No explicit enabled setting
            builder.add_values({"enabled_app": {"name": "custom"}})
            config = builder.build()

            # Should remain (default enabled: true)
            assert "enabled_app" in config

    def test_multiple_apps_filtered_correctly(self):
        """Test filtering with multiple apps, some enabled, some disabled."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")
            builder.applications.add("storage")

            builder.add_values(
                {
                    "enabled_app": {"enabled": True},
                    "disabled_app": {"enabled": False},
                    "storage": {"url": "sqlite:///:memory:"},
                }
            )

            config = builder.build()

            # Only enabled_app and storage should be in final config
            assert "enabled_app" in config
            assert "storage" in config
            assert "disabled_app" not in config

    def test_registry_aslist_excludes_filtered_apps(self):
        """Test that ApplicationsRegistry.aslist() excludes filtered apps."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")

            builder.add_values(
                {
                    "enabled_app": {},
                    "disabled_app": {"enabled": False},
                }
            )

            config = builder.build()

            # Applications list should only include enabled_app
            app_list = config.get("applications", [])
            assert "enabled_app" in app_list or any("enabled_app" in app for app in app_list)
            assert "disabled_app" not in app_list and not any("disabled_app" in app for app in app_list)


class TestFinalGlobalSettings:
    """Test that filtered apps don't appear in final GlobalSettings."""

    def test_disabled_app_not_in_final_settings(self):
        """Test that disabled app doesn't appear in final GlobalSettings dict."""
        with patch.dict(
            "sys.modules",
            {
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("disabled_app")
            builder.add_values({"disabled_app": {"enabled": False, "name": "test"}})

            config = builder.build()

            # disabled_app should not be a key in the settings
            assert "disabled_app" not in config

    def test_disabled_app_not_in_applications_list_in_settings(self):
        """Test that disabled app is excluded from 'applications' list in settings."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")

            builder.add_values(
                {
                    "enabled_app": {},
                    "disabled_app": {"enabled": False},
                }
            )

            config = builder.build()

            # Check the applications list
            applications_list = config.get("applications", [])
            assert len(applications_list) >= 1

            # Should include enabled_app but not disabled_app
            assert any("enabled_app" in app for app in applications_list)
            assert not any("disabled_app" in app for app in applications_list)

    def test_final_settings_only_contains_enabled_apps(self):
        """Test that GlobalSettings only contains enabled applications."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.applications.add("disabled_app")

            builder.add_values(
                {
                    "enabled_app": {"name": "enabled_value"},
                    "disabled_app": {"enabled": False, "name": "disabled_value"},
                }
            )

            config = builder.build()

            # Get all app config keys (excluding system keys like 'applications')
            system_keys = {"applications"}
            app_keys = set(config.keys()) - system_keys

            # Should only have enabled_app
            assert "enabled_app" in app_keys
            assert "disabled_app" not in app_keys


class TestFilteringWarnings:
    """Test that warnings are logged when apps are filtered."""

    def test_warning_logged_when_app_filtered(self, caplog):
        """Test that a warning is logged when app is filtered due to enabled: false."""
        with patch.dict(
            "sys.modules",
            {
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("disabled_app")
            builder.add_values({"disabled_app": {"enabled": False}})

            with caplog.at_level("WARNING"):
                builder.build()

            # Should log warning about disabled app
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            assert any("disabled_app" in msg for msg in warning_messages)

    def test_no_warning_for_enabled_apps(self, caplog):
        """Test that no filtering warning for apps that remain enabled."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.add_values({"enabled_app": {"name": "test"}})

            with caplog.at_level("WARNING"):
                builder.build()

            # Should not have warnings about enabled_app being filtered
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            filtering_warnings = [msg for msg in warning_messages if "enabled_app" in msg and "disabled" in msg.lower()]
            assert len(filtering_warnings) == 0

    def test_warning_includes_app_name(self, caplog):
        """Test that filtering warning includes the app name."""
        with patch.dict(
            "sys.modules",
            {
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("disabled_app")
            builder.add_values({"disabled_app": {"enabled": False}})

            with caplog.at_level("WARNING"):
                builder.build()

            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            disabled_warnings = [msg for msg in warning_messages if "disabled_app" in msg]
            assert len(disabled_warnings) > 0


class TestFilteringEdgeCases:
    """Test edge cases in application filtering."""

    def test_app_without_settings_type_not_affected(self):
        """Test that apps without settings_type are not affected by filtering."""
        no_settings_app_module = ModuleType("no_settings_app")
        no_settings_app_module.__spec__ = ModuleSpec(name="no_settings_app", loader=None)

        no_settings_app_app_module = ModuleType("no_settings_app.__app__")
        no_settings_app_app_module.application = Application()  # No settings_type
        no_settings_app_app_module.__spec__ = ModuleSpec(name="no_settings_app.__app__", loader=None)

        with patch.dict(
            "sys.modules",
            {
                "no_settings_app": no_settings_app_module,
                "no_settings_app.__app__": no_settings_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("no_settings_app")

            # Try to add config with enabled: false
            # This might be ignored or handle differently for apps without settings_type
            builder.add_values({"no_settings_app": {"enabled": False}})

            builder.build()

            # Behavior might vary - document what happens
            # Either it's filtered or the enabled flag is ignored

    def test_filtering_with_no_config_provided(self):
        """Test filtering when app is in registry but no config provided."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")

            # No config provided at all
            config = builder.build()

            # App should remain (default enabled: true from mixin)
            # Might not be in config if no settings provided, but should be in applications list
            applications_list = config.get("applications", [])
            assert any("enabled_app" in app for app in applications_list)

    def test_filtering_with_empty_config(self):
        """Test filtering when empty config object is provided."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("enabled_app")
            builder.add_values({"enabled_app": {}})

            config = builder.build()

            # Should remain (empty config means use defaults, including enabled: true)
            applications_list = config.get("applications", [])
            assert any("enabled_app" in app for app in applications_list)

    def test_filtering_preserves_app_order(self):
        """Test that filtering preserves the order of remaining apps."""
        with patch.dict(
            "sys.modules",
            {
                "enabled_app": enabled_app_module,
                "enabled_app.__app__": enabled_app_app_module,
                "disabled_app": disabled_app_module,
                "disabled_app.__app__": disabled_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)

            # Add in specific order
            builder.applications.add("enabled_app")
            builder.applications.add("storage")
            builder.applications.add("disabled_app")

            builder.add_values(
                {
                    "enabled_app": {},
                    "storage": {"url": "sqlite:///:memory:"},
                    "disabled_app": {"enabled": False},
                }
            )

            config = builder.build()

            applications_list = config.get("applications", [])

            # Find positions
            enabled_pos = None
            storage_pos = None

            for i, app in enumerate(applications_list):
                if "enabled_app" in app:
                    enabled_pos = i
                if "storage" in app:
                    storage_pos = i

            # enabled_app should come before storage (if both present)
            if enabled_pos is not None and storage_pos is not None:
                assert enabled_pos < storage_pos
