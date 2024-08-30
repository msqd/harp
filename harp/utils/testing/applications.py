from functools import cached_property

import pytest

from harp.config import Application, ConfigurationBuilder
from harp.config.asdict import asdict
from harp.config.utils import get_application


class BaseTestForApplications:
    name = None
    config_key = None
    expected_defaults = {}

    @cached_property
    def application(self) -> Application:
        return get_application(self.name)

    @pytest.fixture
    def configuration(self):
        config = ConfigurationBuilder(use_default_applications=False)
        config.applications.add(self.name)
        return config

    def test_default_settings(self):
        """Checks that default settings are as expected by the implementation."""
        computed_defaults = asdict(self.application.settings_type(), verbose=True)
        assert computed_defaults == self.expected_defaults

    def test_default_settings_idempotence(self):
        """Checks that default settings, if used to recrete settings, will keep the same values."""
        defaults_settings = asdict(self.application.settings_type(), verbose=True)
        reparsed_settings = asdict(self.application.settings_type(**defaults_settings), verbose=True)
        assert reparsed_settings == defaults_settings
