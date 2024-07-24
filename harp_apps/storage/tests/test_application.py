import pytest

from harp.config import asdict
from harp.utils.testing.applications import BaseTestForApplications


class TestStorageApplication(BaseTestForApplications):
    name = "harp_apps.storage"
    config_key = "storage"

    expected_defaults = {
        "blobs": {"type": "sql"},
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
    }

    @pytest.mark.parametrize(
        ["settings", "more_settings"],
        [
            [{"url": "sqlite+aiosqlite:///harp.db"}, None],
            [{"migrate": True}, None],
            [{"migrate": False}, None],
            [{"blobs": {"type": "redis"}}, {"blobs": {"type": "redis", "url": "redis://localhost:6379/0"}}],
        ],
    )
    def test_defaults_fills_missing_values_for_sqlalchemy_type(self, settings: dict, more_settings: dict | None):
        assert asdict(self.ApplicationType.Settings(**settings)) == {
            **self.expected_defaults,
            **settings,
            **(more_settings or {}),
        }
