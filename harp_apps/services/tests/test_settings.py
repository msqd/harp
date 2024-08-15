import re

import pytest
from pydantic import ValidationError

from harp.utils.testing import RE

from ..settings import ServicesSettings
from ..settings.database import ALLOWED_SCHEMES


def test_redis_settings_empty():
    settings = ServicesSettings()
    assert settings.model_dump().get("redis") is None


def test_redis_settings_default():
    settings = ServicesSettings.from_kwargs(redis={"url": "redis://localhost:6379/1"})
    assert settings.model_dump(mode="json").get("redis") == {"url": "redis://localhost:6379/1"}
    assert str(settings.redis.url) == "redis://localhost:6379/1"


def test_redis_settings_invalid():
    with pytest.raises(ValidationError):
        ServicesSettings.from_kwargs(redis={"url": "foobar://localhost:6379/1"})


def test_database_settings_empty():
    settings = ServicesSettings()
    assert settings.model_dump().get("database") is None


@pytest.mark.parametrize("scheme", ALLOWED_SCHEMES)
def test_database_settings_default(scheme):
    settings = ServicesSettings.from_kwargs(database={"url": scheme + "://harp:secret@database/harp"})
    assert settings.model_dump(mode="json").get("database") == {
        "url": RE(re.escape(scheme) + r"(\+.*)?" + re.escape("://harp:secret@database/harp"))
    }


def test_database_settings_invalid():
    with pytest.raises(ValidationError):
        ServicesSettings.from_kwargs(database={"url": "foobar://harp:secret@database/harp"})
