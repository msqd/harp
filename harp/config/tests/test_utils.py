from unittest.mock import MagicMock, patch

from harp.config.utils import get_configuration_builder_type


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
