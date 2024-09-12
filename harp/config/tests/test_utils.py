from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from harp.config import Application
from harp.config.utils import get_application, get_configuration_builder_type, resolve_application_name

# fake module for foo.bar
foobar_module = ModuleType("foo.bar")
foobar_module.__spec__ = ModuleSpec(name="foo.bar", loader=None)

# fake module for foo.bar.__app__
foobar_app_module = ModuleType("foo.bar.__app__")
foobar_app_module.application = Application()
foobar_app_module.__spec__ = ModuleSpec(name="foo.bar.__app__", loader=None)

# fake module for acme.storage
acme_storage_module = ModuleType("acme.storage")
acme_storage_module.__spec__ = ModuleSpec(name="acme.storage", loader=None)

# fake module for acme.storage.__app__
acme_storage_app_module = ModuleType("acme.storage.__app__")
acme_storage_app_module.application = Application()
acme_storage_app_module.__spec__ = ModuleSpec(name="acme.storage.__app__", loader=None)


def test_resolve_application_name():
    assert resolve_application_name("storage") == "harp_apps.storage"
    assert resolve_application_name("harp_apps.storage") == "harp_apps.storage"

    with pytest.raises(ModuleNotFoundError):
        resolve_application_name("foo.bar")

    with patch.dict(
        "sys.modules",
        {
            "foo.bar": foobar_module,
        },
    ):
        assert resolve_application_name("foo.bar") == "foo.bar"

    # check that our resolver do not resolve if the module is not available anymore (to test one issue we add because
    # of an added lru_cache)
    with pytest.raises(ModuleNotFoundError):
        resolve_application_name("foo.bar")


def test_get_application():
    storage_app = get_application("storage")
    assert get_application("harp_apps.storage") is storage_app
    assert get_application("storage") is storage_app


def test_get_overriden_application():
    with patch.dict(
        "sys.modules",
        {
            "acme.storage": acme_storage_module,
            "acme.storage.__app__": acme_storage_app_module,
        },
    ):
        storage_app = get_application("acme.storage")
        assert get_application("acme.storage") is storage_app
        assert get_application("storage") is not storage_app


@patch("os.environ.get")
@patch("builtins.__import__")
def test_get_configuration_builder_type_with_custom_edition(mock_import, mock_get_env):
    # Mock environment variable
    mock_get_env.return_value = "custom_edition"

    # Mock import of the custom edition
    mock_module = MagicMock()
    mock_import.return_value = mock_module
    mock_module.ConfigurationBuilder = "MockedCustomConfigurationBuilder"

    result = get_configuration_builder_type()
    assert result == "MockedCustomConfigurationBuilder"


def test_get_configuration_builder_type_fallback_to_default_edition():
    with patch.dict("os.environ", {"HARP_EDITION": "non_existent_edition"}):
        result = get_configuration_builder_type()
        assert result.__name__ == "ConfigurationBuilder"
        assert result.__module__ == "harp.config.builders.configuration"
