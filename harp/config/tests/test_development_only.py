import logging

import pytest

import harp
from harp.config import ConfigurationBuilder
from harp.config.development_only import development_only_settings
from harp.typedefs import GlobalSettings
from harp_apps.dashboard.settings import DashboardSettings
from harp_apps.storage.settings import StorageSettings

POSTGRES = "postgresql+asyncpg://user:pass@db/harp"


@pytest.fixture(autouse=True)
def debug_off(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", False)


def settings(*, storage=POSTGRES, auth=None):
    return GlobalSettings(
        {
            "storage": StorageSettings(url=storage),
            "dashboard": DashboardSettings(auth=auth),
        }
    )


def names(config):
    return [item.name for item in development_only_settings(config)]


def test_production_grade_settings_are_silent():
    assert names(settings()) == []


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite:///harp.db", "sqlite+aiosqlite:///harp.db"])
def test_sqlite_storage(url):
    assert names(settings(storage=url)) == ["storage.url"]


def test_default_storage_is_sqlite():
    assert names(GlobalSettings({"storage": StorageSettings()})) == ["storage.url"]


def test_dashboard_without_auth_is_not_development_only():
    assert names(settings(auth=None)) == []


def test_dashboard_auth_none():
    assert names(settings(auth={"type": "none"})) == ["dashboard.auth.type"]


def test_debug(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", True)
    assert names(settings()) == ["HARP_DEBUG"]


def test_missing_applications_are_ignored():
    assert names(GlobalSettings()) == []


def test_each_item_says_what_to_use_instead():
    (item,) = development_only_settings(settings(storage="sqlite:///:memory:"))
    assert "PostgreSQL" in item.message


async def test_startup_logs_one_warning_per_setting(caplog):
    builder = ConfigurationBuilder(use_default_applications=False)
    for app in ("http_client", "proxy", "storage", "dashboard"):
        builder.applications.add(app)
    builder.add_values(
        {
            "storage": {"url": "sqlite:///:memory:"},
            "dashboard": {"auth": {"type": "none"}, "devserver": {"enabled": False}},
        }
    )
    with caplog.at_level(logging.WARNING):
        system = await builder.abuild_system(validate_dependencies=False)
    await system.dispose()
    warned = [r.getMessage() for r in caplog.records if "development" in r.getMessage().lower()]
    assert len(warned) == 2
    assert sum("dashboard.auth.type" in m for m in warned) == 1
