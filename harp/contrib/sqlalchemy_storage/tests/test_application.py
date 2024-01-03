import pytest
from pytest import fixture

from harp import Config


class BaseTestForApplications:
    name = None
    config_key = None

    expected_defaults = {}

    @fixture
    def configuration(self):
        config = Config()
        config.add_application(self.name)
        return config

    @fixture
    def ApplicationType(self, configuration):
        return configuration.get_application_type(self.name)

    def test_default_settings_on_none_passed(self, ApplicationType):
        assert ApplicationType.defaults() == self.expected_defaults

    def test_default_settings_on_empty_dict_passed(self, ApplicationType):
        settings = {}
        assert ApplicationType.defaults(settings) == {}

    def test_instanciate_with_default_settings(self, ApplicationType):
        defaults = ApplicationType.defaults()
        application = ApplicationType(defaults)
        assert application.validate() == defaults


class TestSqlAlchemyStorageApplication(BaseTestForApplications):
    name = "harp.contrib.sqlalchemy_storage"
    config_key = "storage"

    expected_defaults = {
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///:memory:",
        "drop_tables": False,
        "echo": False,
    }

    @pytest.mark.parametrize(
        "settings",
        [
            {"type": "foo"},
            {"something": "different"},
        ],
    )
    def test_defaults_does_not_change_anything_if_not_sqlalchemy_type(self, ApplicationType, settings):
        assert ApplicationType.defaults(settings) == settings

    @pytest.mark.parametrize(
        "settings",
        [
            {"type": "sqlalchemy", "url": "sqlite+aiosqlite:///harp.db"},
            {"type": "sqlalchemy", "echo": True},
            {"type": "sqlalchemy", "drop_tables": True},
        ],
    )
    def test_defaults_fills_missing_values_for_sqlalchemy_type(self, ApplicationType, settings):
        assert ApplicationType.defaults(settings) == {**self.expected_defaults, **settings}
