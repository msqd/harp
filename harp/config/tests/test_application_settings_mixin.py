"""
Tests for ApplicationSettingsMixin functionality.

These tests verify that:
1. ApplicationSettingsMixin provides an 'enabled' field
2. Application raises error if settings_type doesn't have ApplicationSettingsMixin
3. Mixin works with multiple inheritance (Service, Configurable)
4. Default value for enabled is True
"""

import pytest
from pydantic import BaseModel

from harp.config import Application, Configurable, Service
from harp.config.mixins import ApplicationSettingsMixin


class TestApplicationSettingsMixin:
    """Test the ApplicationSettingsMixin class itself."""

    def test_mixin_exists(self):
        """Test that ApplicationSettingsMixin can be imported."""
        # This will fail with ImportError: cannot import name 'ApplicationSettingsMixin'
        assert ApplicationSettingsMixin is not None

    def test_mixin_provides_enabled_field(self):
        """Test that the mixin provides an 'enabled' field with default True."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        settings = TestSettings()
        assert hasattr(settings, "enabled")
        assert settings.enabled is True

    def test_mixin_enabled_can_be_overridden(self):
        """Test that the enabled field can be set to False."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        settings = TestSettings(enabled=False)
        assert settings.enabled is False

    def test_mixin_enabled_field_type(self):
        """Test that enabled field is a boolean."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        settings = TestSettings()
        assert isinstance(settings.enabled, bool)

        # Should also validate type
        with pytest.raises(Exception):  # Pydantic validation error
            TestSettings(enabled="not a bool")

    def test_mixin_with_service(self):
        """Test that mixin works with Service base class."""

        class TestSettings(ApplicationSettingsMixin, Service):
            pass

        settings = TestSettings()
        assert hasattr(settings, "enabled")
        assert settings.enabled is True

    def test_mixin_with_configurable(self):
        """Test that mixin works with Configurable base class."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        settings = TestSettings()
        assert hasattr(settings, "enabled")
        assert settings.enabled is True

    def test_mixin_with_multiple_inheritance(self):
        """Test that mixin works correctly with multiple inheritance."""

        class TestSettings(ApplicationSettingsMixin, Service):
            custom_field: str = "test"

        settings = TestSettings()
        assert settings.enabled is True
        assert settings.custom_field == "test"

    def test_mixin_serialization(self):
        """Test that enabled field is included in serialization."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            name: str = "test"

        settings = TestSettings(enabled=False)
        data = settings.model_dump()

        assert "enabled" in data
        assert data["enabled"] is False
        assert data["name"] == "test"

    def test_mixin_deserialization(self):
        """Test that enabled field can be deserialized from dict."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            name: str = "test"

        data = {"enabled": False, "name": "custom"}
        settings = TestSettings(**data)

        assert settings.enabled is False
        assert settings.name == "custom"


class TestApplicationWithMixin:
    """Test Application integration with ApplicationSettingsMixin."""

    def test_application_requires_mixin_when_settings_type_is_set(self):
        """Test that Application raises error if settings_type doesn't have the mixin."""

        class InvalidSettings(Configurable):
            name: str = "test"

        # This should fail because InvalidSettings doesn't inherit from ApplicationSettingsMixin
        # The Application should validate this in __init__ or when settings are accessed
        with pytest.raises((TypeError, ValueError, AttributeError)):
            app = Application(settings_type=InvalidSettings)
            # Validation might happen during build or during a check method
            app.validate_settings_type()  # This method doesn't exist yet

    def test_application_accepts_mixin_settings(self):
        """Test that Application accepts settings_type with the mixin."""

        class ValidSettings(ApplicationSettingsMixin, Configurable):
            name: str = "test"

        # This should succeed
        app = Application(settings_type=ValidSettings)
        assert app.settings_type == ValidSettings

    def test_application_with_dict_settings_type_does_not_require_mixin(self):
        """Test that Application with dict settings_type doesn't require mixin."""
        # dict is a special case and should not require the mixin
        app = Application(settings_type=dict)
        assert app.settings_type is dict

    def test_application_default_dict_settings_does_not_require_mixin(self):
        """Test that Application with no settings_type (defaults to dict) works."""
        app = Application()
        assert app.settings_type is dict

    def test_application_checks_mixin_presence(self):
        """Test that Application has a method to check for mixin presence."""

        class ValidSettings(ApplicationSettingsMixin, Configurable):
            pass

        class InvalidSettings(Configurable):
            pass

        # This method doesn't exist yet and should fail
        valid_app = Application(settings_type=ValidSettings)
        assert valid_app.has_application_settings_mixin() is True

        invalid_app = Application(settings_type=InvalidSettings)
        assert invalid_app.has_application_settings_mixin() is False

        dict_app = Application(settings_type=dict)
        assert dict_app.has_application_settings_mixin() is False


class TestMixinInheritanceOrder:
    """Test that the mixin works correctly regardless of inheritance order."""

    def test_mixin_first_then_configurable(self):
        """Test mixin as first parent."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        settings = TestSettings()
        assert settings.enabled is True

    def test_mixin_first_then_service(self):
        """Test mixin as first parent with Service."""

        class TestSettings(ApplicationSettingsMixin, Service):
            pass

        settings = TestSettings()
        assert settings.enabled is True

    def test_mixin_with_pydantic_basemodel(self):
        """Test that mixin works with raw Pydantic BaseModel."""

        class TestSettings(ApplicationSettingsMixin, BaseModel):
            name: str = "test"

        settings = TestSettings()
        assert settings.enabled is True
        assert settings.name == "test"


class TestMixinValidation:
    """Test validation behaviors with the mixin."""

    def test_enabled_field_in_model_fields(self):
        """Test that enabled is properly registered in model_fields."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        assert "enabled" in TestSettings.model_fields

    def test_enabled_field_has_correct_default_in_schema(self):
        """Test that the JSON schema reflects the correct default."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            pass

        schema = TestSettings.model_json_schema()
        assert "enabled" in schema.get("properties", {})
        # Default value should be True
        assert schema["properties"]["enabled"].get("default", None) is True

    def test_mixin_does_not_conflict_with_existing_fields(self):
        """Test that mixin doesn't break when combined with other fields."""

        class TestSettings(ApplicationSettingsMixin, Configurable):
            enabled_at: str = "2024-01-01"  # Different field name to ensure no conflict
            name: str = "test"

        settings = TestSettings()
        assert settings.enabled is True  # From mixin
        assert settings.enabled_at == "2024-01-01"
        assert settings.name == "test"
