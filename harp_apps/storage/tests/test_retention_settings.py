"""Transaction retention is a storage setting. `janitor.old_after` is its deprecated alias."""

import logging

import pytest
from pydantic import ValidationError

from harp.config import ConfigurationBuilder
from harp_apps.storage.settings import StorageSettings


def build(caplog, **values):
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.add_values(values)
    with caplog.at_level(logging.WARNING):
        return builder.build()


def deprecations(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if "old_after" in r.getMessage()]


def test_default_retention_is_sixty_days():
    assert StorageSettings().retention_days == 60


@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_retention_is_rejected(value):
    with pytest.raises(ValidationError):
        StorageSettings(retention_days=value)


def test_storage_key_sets_the_retention(caplog):
    settings = build(caplog, storage={"retention_days": 14})

    assert settings["storage"].retention_days == 14
    assert deprecations(caplog) == []


def test_without_any_key_the_retention_is_the_default_and_nothing_is_warned(caplog):
    settings = build(caplog)

    assert settings["storage"].retention_days == 60
    assert deprecations(caplog) == []


def test_janitor_old_after_still_sets_the_retention_and_warns_naming_the_new_key(caplog):
    settings = build(caplog, janitor={"old_after": 30})

    assert settings["storage"].retention_days == 30
    (message,) = deprecations(caplog)
    assert "storage.retention_days" in message


def test_the_storage_key_wins_over_the_alias_and_warns(caplog):
    settings = build(caplog, janitor={"old_after": 30}, storage={"retention_days": 14})

    assert settings["storage"].retention_days == 14
    (message,) = deprecations(caplog)
    assert "storage.retention_days" in message
    assert "ignored" in message
