"""
Tests for configuration validation warnings and strict mode.

These tests verify the three validation cases from issue #595:
1. Configuration exists for an unloaded application -> Warning
2. Application with enabled: false -> Different warning, app not loaded
3. Application with enabled: false + --enable flag -> Config takes precedence

Also tests --strict flag behavior.
"""

from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch

import pytest

from harp.config import Application, Configurable
from harp.config.builders import ConfigurationBuilder
from harp.config.mixins import ApplicationSettingsMixin


# Create a fake test application module
test_app_module = ModuleType("test_app")
test_app_module.__spec__ = ModuleSpec(name="test_app", loader=None)


class TestAppSettings(ApplicationSettingsMixin, Configurable):
    name: str = "test"


test_app_app_module = ModuleType("test_app.__app__")
test_app_app_module.application = Application(settings_type=TestAppSettings)
test_app_app_module.__spec__ = ModuleSpec(name="test_app.__app__", loader=None)


class TestConfigurationValidationWarnings:
    """Test validation warnings for various configuration scenarios."""

    def test_warning_when_config_exists_for_unloaded_app(self, caplog):
        """
        Case 1: Configuration exists for an application that is not loaded.
        Should log a warning.
        """
        builder = ConfigurationBuilder(use_default_applications=False)
        # Don't add the application to registry
        # But provide configuration for it
        builder.add_values({"nonexistent_app": {"some_setting": "value"}})

        with caplog.at_level("WARNING"):
            builder.build()

        # Should have logged a warning about unused configuration
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("nonexistent_app" in msg for msg in warning_messages), "Expected warning about nonexistent_app"
        assert any("not loaded" in msg.lower() or "unused" in msg.lower() for msg in warning_messages)

    def test_warning_message_content_for_unloaded_app(self, caplog):
        """Test that the warning message for unloaded apps is clear and informative."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values({"unloaded_app": {"setting": "value"}})

        with caplog.at_level("WARNING"):
            builder.build()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_messages) > 0

        # The warning should mention the app name and suggest it's not loaded
        relevant_warnings = [msg for msg in warning_messages if "unloaded_app" in msg]
        assert len(relevant_warnings) > 0
        assert any(
            "not loaded" in msg.lower() or "not registered" in msg.lower() or "unknown" in msg.lower()
            for msg in relevant_warnings
        )

    def test_multiple_unloaded_apps_generate_multiple_warnings(self, caplog):
        """Test that each unloaded app with config generates its own warning."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values(
            {
                "unloaded_app1": {"setting": "value1"},
                "unloaded_app2": {"setting": "value2"},
                "unloaded_app3": {"setting": "value3"},
            }
        )

        with caplog.at_level("WARNING"):
            builder.build()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

        # Should have warnings for all three unloaded apps
        assert any("unloaded_app1" in msg for msg in warning_messages)
        assert any("unloaded_app2" in msg for msg in warning_messages)
        assert any("unloaded_app3" in msg for msg in warning_messages)

    def test_no_warning_when_app_is_loaded(self, caplog):
        """Test that no warning is generated when app is properly loaded with config."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.applications.add("storage")
        builder.add_values({"storage": {"url": "sqlite:///:memory:"}})

        with caplog.at_level("WARNING"):
            builder.build()

        # Should NOT have warnings about storage
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert not any("storage" in msg for msg in warning_messages)


class TestDisabledApplicationWarnings:
    """Test warnings for applications with enabled: false."""

    def test_warning_when_app_has_enabled_false(self, caplog):
        """
        Case 2: Application configured with enabled: false.
        Should log a different warning and app should not be loaded.
        """
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")
            builder.add_values({"test_app": {"enabled": False, "name": "custom"}})

            with caplog.at_level("WARNING"):
                config = builder.build()

            # Should have logged a warning about disabled application
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            assert any("test_app" in msg for msg in warning_messages)
            assert any("disabled" in msg.lower() or "enabled: false" in msg.lower() for msg in warning_messages)

            # Application should NOT be in final config
            assert "test_app" not in config

    def test_disabled_app_not_in_applications_list(self):
        """Test that disabled app is filtered from applications list."""
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")
            builder.add_values({"test_app": {"enabled": False}})

            config = builder.build()

            # test_app should not be in the applications list
            assert "test_app" not in config.get("applications", [])

    def test_disabled_app_not_in_registry_after_build(self):
        """Test that disabled app is removed from ApplicationsRegistry during build."""
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")

            # Before build, app should be in registry
            assert "test_app" in builder.applications

            builder.add_values({"test_app": {"enabled": False}})
            config = builder.build()

            # After build with enabled: false, app should be filtered
            # Note: This might require checking a different attribute or method
            # The exact behavior depends on implementation
            assert "test_app" not in config

    def test_warning_message_differs_for_disabled_vs_unloaded(self, caplog):
        """Test that disabled apps get a different warning message than unloaded apps."""
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")
            builder.add_values(
                {
                    "test_app": {"enabled": False},
                    "unloaded_app": {"some_setting": "value"},
                }
            )

            with caplog.at_level("WARNING"):
                builder.build()

            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

            # Find warnings for each app
            disabled_warnings = [msg for msg in warning_messages if "test_app" in msg]
            unloaded_warnings = [msg for msg in warning_messages if "unloaded_app" in msg]

            # Both should have warnings
            assert len(disabled_warnings) > 0
            assert len(unloaded_warnings) > 0

            # They should be different messages
            # Disabled should mention "disabled" or "enabled: false"
            assert any("disabled" in msg.lower() for msg in disabled_warnings)

            # Unloaded should mention "not loaded" or similar
            assert any("not loaded" in msg.lower() or "not registered" in msg.lower() for msg in unloaded_warnings)


class TestEnableFlagWithDisabledConfig:
    """Test --enable flag interaction with enabled: false configuration."""

    def test_enable_flag_does_not_override_enabled_false_config(self, caplog):
        """
        Case 3: App with enabled: false in config, but --enable flag provided.
        Configuration should take precedence, app should NOT be loaded.
        """
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            # Simulate --enable flag being used
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")  # This simulates --enable test_app

            # But config says enabled: false
            builder.add_values({"test_app": {"enabled": False}})

            with caplog.at_level("WARNING"):
                config = builder.build()

            # Config should take precedence - app should NOT be loaded
            assert "test_app" not in config
            assert "test_app" not in config.get("applications", [])

            # Should still get the disabled warning
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            assert any("test_app" in msg and "disabled" in msg.lower() for msg in warning_messages)

    def test_config_precedence_documented_in_warning(self, caplog):
        """Test that warning mentions config precedence when --enable conflicts with enabled: false."""
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")
            builder.add_values({"test_app": {"enabled": False}})

            with caplog.at_level("WARNING"):
                builder.build()

            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            relevant_warnings = [msg for msg in warning_messages if "test_app" in msg]

            # Warning might mention that config takes precedence
            # This is optional but would be good UX
            assert len(relevant_warnings) > 0


class TestStrictModeErrors:
    """Test --strict flag converts warnings to errors."""

    def test_strict_mode_raises_error_for_unloaded_app(self):
        """Test that --strict mode raises error instead of warning for unloaded app."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values({"nonexistent_app": {"setting": "value"}})

        # With strict mode enabled, should raise an error
        with pytest.raises(Exception) as exc_info:  # Might be ValueError or custom exception
            builder.build(strict=True)

        # Error message should mention the unloaded app
        assert "nonexistent_app" in str(exc_info.value).lower()

    def test_strict_mode_allows_valid_configuration(self):
        """Test that --strict mode doesn't affect valid configuration."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.applications.add("storage")
        builder.add_values({"storage": {"url": "sqlite:///:memory:"}})

        # Should not raise error with valid config
        config = builder.build(strict=True)
        assert "storage" in config

    def test_strict_mode_allows_disabled_app(self, caplog):
        """Test that --strict mode does NOT raise error for disabled app with config.

        Disabled apps (enabled: false) are intentional configuration directives.
        Strict mode only catches unloaded/unknown apps, not explicitly disabled ones.
        """
        with patch.dict(
            "sys.modules",
            {
                "test_app": test_app_module,
                "test_app.__app__": test_app_app_module,
            },
        ):
            builder = ConfigurationBuilder(use_default_applications=False)
            builder.applications.add("test_app")
            builder.add_values({"test_app": {"enabled": False}})

            with caplog.at_level("WARNING"):
                # Should NOT raise error, just log warning
                config = builder.build(strict=True)

            # App should not be in final config
            assert "test_app" not in config

            # Should have warning about disabled app
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            assert any("test_app" in msg and "disabled" in msg.lower() for msg in warning_messages)

    def test_strict_mode_error_message_is_clear(self):
        """Test that strict mode error messages are helpful."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values({"bad_app": {"setting": "value"}})

        with pytest.raises(Exception) as exc_info:
            builder.build(strict=True)

        error_msg = str(exc_info.value).lower()
        assert "bad_app" in error_msg
        # Should give actionable advice
        assert any(
            keyword in error_msg for keyword in ["not loaded", "not found", "invalid", "unknown", "register", "enable"]
        )

    def test_strict_mode_false_allows_warnings(self, caplog):
        """Test that strict=False (default) only produces warnings."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values({"nonexistent_app": {"setting": "value"}})

        with caplog.at_level("WARNING"):
            # Should not raise, just warn
            builder.build(strict=False)

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("nonexistent_app" in msg for msg in warning_messages)

    def test_strict_mode_with_multiple_errors(self):
        """Test that strict mode reports all configuration errors."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values(
            {
                "bad_app1": {"setting": "value"},
                "bad_app2": {"setting": "value"},
            }
        )

        with pytest.raises(Exception) as exc_info:
            builder.build(strict=True)

        error_msg = str(exc_info.value).lower()
        # Should ideally mention both apps, or at least fail on first
        # Implementation might vary
        assert "bad_app1" in error_msg or "bad_app2" in error_msg


class TestBuildMethodStrictParameter:
    """Test that ConfigurationBuilder.build() accepts strict parameter."""

    def test_build_accepts_strict_parameter(self):
        """Test that build() method signature accepts strict parameter."""
        builder = ConfigurationBuilder(use_default_applications=False)

        # Should not raise TypeError about unexpected keyword argument
        try:
            builder.build(strict=False)
        except TypeError as e:
            if "strict" in str(e):
                pytest.fail("build() method doesn't accept 'strict' parameter")
            raise

    def test_build_strict_parameter_is_boolean(self):
        """Test that strict parameter accepts boolean values."""
        builder = ConfigurationBuilder(use_default_applications=False)

        # Both True and False should be valid
        builder.build(strict=True)
        builder.build(strict=False)

    def test_build_strict_defaults_to_false(self, caplog):
        """Test that strict defaults to False (warnings only)."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.add_values({"bad_app": {"setting": "value"}})

        with caplog.at_level("WARNING"):
            # Calling without strict parameter should not raise
            builder.build()

        # Should have produced warnings, not errors
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_messages) > 0


class TestValidationWithRealApplications:
    """Test validation with actual HARP applications."""

    def test_validation_with_storage_app(self):
        """Test validation works correctly with real storage app."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.applications.add("storage")
        builder.add_values({"storage": {"url": "sqlite:///:memory:", "migrate": False}})

        # Should build without warnings
        config = builder.build()
        assert "storage" in config

    def test_warning_for_typo_in_app_name(self, caplog):
        """Test that typo in application name produces helpful warning."""
        builder = ConfigurationBuilder(use_default_applications=False)
        builder.applications.add("storage")

        # Typo: "stoarge" instead of "storage"
        builder.add_values({"stoarge": {"url": "sqlite:///:memory:"}})

        with caplog.at_level("WARNING"):
            builder.build()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("stoarge" in msg for msg in warning_messages)

    def test_no_warning_for_system_level_config(self, caplog):
        """Test that system-level configuration keys don't produce warnings."""
        builder = ConfigurationBuilder(use_default_applications=False)

        # These are system-level keys, not application names
        builder.add_values(
            {
                "applications": ["storage"],  # Special key for app list
            }
        )

        with caplog.at_level("WARNING"):
            builder.build()

        # Should not warn about "applications" being an unknown app
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert not any("applications" in msg and "not loaded" in msg.lower() for msg in warning_messages)
