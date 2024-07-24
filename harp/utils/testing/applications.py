from functools import cached_property

import pytest

from harp.config import ConfigurationBuilder, asdict
from harp.config.utils import get_application_type


class BaseTestForApplications:
    name = None
    config_key = None
    expected_defaults = {}

    @cached_property
    def ApplicationType(self):
        return get_application_type(self.name)

    @pytest.fixture
    def configuration(self):
        config = ConfigurationBuilder(use_default_applications=False)
        config.applications.add(self.name)
        return config

    def test_default_settings(self):
        """Checks that default settings are as expected by the implementation."""
        computed_defaults = asdict(self.ApplicationType.Settings())
        assert computed_defaults == self.expected_defaults

    def test_default_settings_idempotence(self):
        """Checks that default settings, if used to recrete settings, will keep the same values."""
        defaults_settings = asdict(self.ApplicationType.Settings())
        reparsed_settings = asdict(self.ApplicationType.Settings(**defaults_settings))
        assert reparsed_settings == defaults_settings
