"""A storage boot or migration failure never writes the database password to the logs."""

import logging
import sys
import traceback

import pytest
from pydantic_core import MultiHostUrl

from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder

PASSWORD = "Top@Secret"
ENCODED_PASSWORD = "Top%40Secret"
URL = f"postgresql+asyncpg://enc:{ENCODED_PASSWORD}@127.0.0.1:1/harp"
# asyncpg also reads the password from the query string
QUERY_URL = f"postgresql+asyncpg://enc@127.0.0.1:1/harp?password={ENCODED_PASSWORD}"


def _unreachable_host(monkeypatch, url):
    pass


def _missing_driver(monkeypatch, url):
    monkeypatch.setitem(sys.modules, "asyncpg", None)


def _error_embedding_the_url(monkeypatch, url):
    def fail(*args, **kwargs):
        raise ValueError(f"invalid interpolation syntax in '{url}' at position 48")

    monkeypatch.setattr("alembic.command.upgrade", fail)


class _AttributeError(Exception):
    """Builds its text from an attribute, like DBAPIError and asyncpg errors do."""

    def __init__(self, url):
        super().__init__("failed")
        self.detail = url

    def __str__(self):
        return f"failed: {self.detail}"


def _error_rendering_an_attribute(monkeypatch, url):
    def fail(*args, **kwargs):
        raise _AttributeError(url)

    monkeypatch.setattr("alembic.command.upgrade", fail)


def _error_chained_to_one_embedding_the_url(monkeypatch, url):
    def fail(*args, **kwargs):
        try:
            raise ValueError(f"cannot connect to {url}")
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
@pytest.mark.parametrize("url", [URL, QUERY_URL])
async def test_boot_failure_logs_no_password(failure, url, monkeypatch, caplog):
    failure(monkeypatch, url)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(Exception) as exc_info:
        await _boot(url)

    logged = "\n".join(
        [record.getMessage() for record in caplog.records]
        + [record.exc_text or "" for record in caplog.records]
        + ["".join(traceback.format_exception(*record.exc_info)) for record in caplog.records if record.exc_info]
    )
    raised = "".join(traceback.format_exception(exc_info.value))
    for text in (logged, raised):
        assert PASSWORD not in text
        assert ENCODED_PASSWORD not in text


@pytest.mark.parametrize("password", ["Top@Secret", "Ab+cd@ef", "sp ace%x"])
async def test_failure_outside_migrations_logs_no_password(password, monkeypatch, caplog):
    """The schema check runs without migrations (``migrate: false``); its failures are masked too."""
    from sqlalchemy import URL

    url = URL.create("postgresql+asyncpg", username="enc", password=password, host="127.0.0.1", port=1, database="harp")
    rendered = url.render_as_string(hide_password=False)

    async def fail(engine):
        raise ValueError(f"cannot check {rendered}")

    monkeypatch.setattr("harp_apps.storage.utils.migrations.ensure_schema_is_current", fail)
    caplog.set_level(logging.DEBUG)
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": rendered, "migrate": False}, "proxy": {}})
    config = builder.build()

    with pytest.raises(Exception) as exc_info:
        await SystemBuilder(builder.applications, config).abuild()

    logged = "\n".join(
        [record.getMessage() for record in caplog.records]
        + ["".join(traceback.format_exception(*record.exc_info)) for record in caplog.records if record.exc_info]
    )
    raised = "".join(traceback.format_exception(exc_info.value))
    for text in (logged, raised):
        assert password not in text
        assert rendered not in text
        assert rendered.split(":", 2)[2].split("@")[0] not in text


@pytest.mark.parametrize("password", ["Ab+cd@ef", "sp ace%x", "plain", "a/b?c#d:e"])
def test_hide_password_masks_every_rendering_of_the_password(password):
    from sqlalchemy import URL

    from harp_apps.storage.utils.migrations import hide_password

    url = URL.create("postgresql+asyncpg", username="u", password=password, host="db", database="h")
    rendered = url.render_as_string(hide_password=False)
    encoded = rendered.split(":", 2)[2].split("@")[0]

    masked = hide_password(
        f"bad {rendered}; config {rendered.replace('%', '%%')}; settings {MultiHostUrl(rendered)}", url
    )

    assert masked.count("u:***@db/h") == 3
    assert password not in masked
    assert encoded not in masked


@pytest.mark.parametrize("password", ["Ab+cd@ef", "sp ace%x", "a/b?c#d:e"])
def test_a_failure_holding_the_password_anywhere_is_masked(password):
    from sqlalchemy import URL

    from harp_apps.storage.utils.migrations import mask_failure

    url = URL.create("postgresql+asyncpg", username="u", password=password, host="db", database="h")
    rendered = url.render_as_string(hide_password=False)
    encoded = rendered.split(":", 2)[2].split("@")[0]

    masked = str(mask_failure(ValueError(f"bad {rendered}; config {rendered.replace('%', '%%')}"), url))

    assert password not in masked
    assert encoded not in masked
