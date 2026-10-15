import pytest
from pydantic import ValidationError

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp_apps.janitor.settings import JanitorSettings


def test_defaults():
    assert asdict(JanitorSettings(), verbose=True) == {"enabled": True, "period": 600, "old_after": 60}


@pytest.mark.parametrize("field", ["period", "old_after"])
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        JanitorSettings(**{field: value})


def test_non_positive_values_are_rejected_at_configuration_load():
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.add_values({"janitor": {"period": 0}})
    with pytest.raises(ValidationError):
        builder.build()


def test_disabled_janitor_is_not_loaded():
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.add_values({"janitor": {"enabled": False}})
    builder.build()
    assert "janitor" not in builder.applications


def test_configuration_exposes_janitor_settings():
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.add_values({"janitor": {"period": 30}})
    settings = builder.build()
    assert settings["janitor"].period == 30
    assert settings["janitor"].old_after == 60
