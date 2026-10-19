"""A storage boot or migration failure never writes the database password to the logs."""

import logging
import sys
import traceback

import pytest

from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder

PASSWORD = "Top@Secret"
ENCODED_PASSWORD = "Top%40Secret"
URL = f"postgresql+asyncpg://enc:{ENCODED_PASSWORD}@127.0.0.1:1/harp"


def _unreachable_host(monkeypatch):
    pass


def _missing_driver(monkeypatch):
    monkeypatch.setitem(sys.modules, "asyncpg", None)


def _error_embedding_the_url(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError(f"invalid interpolation syntax in '{URL}' at position 48")

    monkeypatch.setattr("alembic.command.upgrade", fail)


class _AttributeError(Exception):
    """Builds its text from an attribute, like DBAPIError and asyncpg errors do."""

    def __init__(self):
        super().__init__("failed")
        self.detail = URL

    def __str__(self):
        return f"failed: {self.detail}"


def _error_rendering_an_attribute(monkeypatch):
    def fail(*args, **kwargs):
        raise _AttributeError()

    monkeypatch.setattr("alembic.command.upgrade", fail)


def _error_chained_to_one_embedding_the_url(monkeypatch):
    def fail(*args, **kwargs):
        try:
            raise ValueError(f"cannot connect to {URL}")
        except ValueError as exc:
            raise OSError("storage unavailable") from exc

    monkeypatch.setattr("alembic.command.upgrade", fail)


async def _boot(url):
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": url}, "proxy": {}})
    config = builder.build()
    await SystemBuilder(builder.applications, config).abuild()


@pytest.mark.parametrize(
    "failure",
    [
        _unreachable_host,
        _missing_driver,
        _error_embedding_the_url,
        _error_rendering_an_attribute,
        _error_chained_to_one_embedding_the_url,
    ],
)
async def test_boot_failure_logs_no_password(failure, monkeypatch, caplog):
    failure(monkeypatch)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(Exception) as exc_info:
        await _boot(URL)

    logged = "\n".join(
        [record.getMessage() for record in caplog.records]
        + [record.exc_text or "" for record in caplog.records]
        + ["".join(traceback.format_exception(*record.exc_info)) for record in caplog.records if record.exc_info]
    )
    raised = "".join(traceback.format_exception(exc_info.value))
    for text in (logged, raised):
        assert PASSWORD not in text
        assert ENCODED_PASSWORD not in text
