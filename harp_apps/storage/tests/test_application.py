import copy

import pytest

from harp.config.asdict import asdict
from harp.utils.testing.applications import BaseTestForApplications


class TestStorageApplication(BaseTestForApplications):
    name = "harp_apps.storage"
    config_key = "storage"

    expected_defaults = {
        "blobs": {"type": "sql"},
        "migrate": True,
        "redis": None,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
    }

    @pytest.mark.parametrize(
        ["settings"],
        [
            [{"url": "sqlite+aiosqlite:///harp.db"}],
            [{"migrate": True}],
            [{"migrate": False}],
            [
                {
                    "blobs": {"type": "redis"},
                    "redis": {"url": "redis://localhost:6379/1"},
                }
            ],
        ],
    )
    def test_defaults_fills_missing_values_for_sqlalchemy_type(self, settings: dict):
        application_settings = self.application.settings_type(**copy.deepcopy(settings))
        assert asdict(application_settings, verbose=True) == {
            **self.expected_defaults,
            **settings,
        }
