import pytest

from harp.utils.testing.applications import BaseTestForApplications


class TestSqlAlchemyStorageApplication(BaseTestForApplications):
    name = "harp_apps.sqlalchemy_storage"
    config_key = "storage"

    expected_defaults = {
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///:memory:",
        "migrate": True,
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
            {"type": "sqlalchemy", "migrate": True},
            {"type": "sqlalchemy", "migrate": False},
        ],
    )
    def test_defaults_fills_missing_values_for_sqlalchemy_type(self, ApplicationType, settings):
        assert ApplicationType.defaults(settings) == {**self.expected_defaults, **settings}
