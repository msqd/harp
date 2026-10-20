"""A storage url rejected by the settings validation never echoes its password."""

import pytest
from pydantic import ValidationError

from harp.config.builders import ConfigurationBuilder
from harp_apps.storage.settings import StorageSettings

PASSWORD = "S3cr3tPw"


def _unknown_scheme(monkeypatch):
    return f"postgresql+nodrv://u:{PASSWORD}@db/h"


def _empty_host(monkeypatch):
    return f"postgresql+asyncpg://u:{PASSWORD}@/h"


@pytest.mark.parametrize("failure", [_unknown_scheme, _empty_host])
def test_rejected_url_does_not_echo_the_password(failure, monkeypatch):
    url = failure(monkeypatch)

    with pytest.raises(ValidationError) as exc_info:
        StorageSettings(url=url)

    message = str(exc_info.value)
    assert "url" in message
    for fragment in (PASSWORD, "S3cr", "cr3t", "tPw"):
        assert fragment not in message


@pytest.mark.parametrize("failure", [_unknown_scheme, _empty_host])
def test_rejected_url_in_configuration_does_not_echo_the_password(failure, monkeypatch):
    url = failure(monkeypatch)
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": url}})

    with pytest.raises(Exception) as exc_info:
        builder.build()

    assert PASSWORD not in str(exc_info.value)
