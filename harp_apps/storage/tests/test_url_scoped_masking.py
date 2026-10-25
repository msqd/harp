"""The storage password is masked where it sits in a url (userinfo, ``?password=``), never as free text.

A password is often a common word, or the user or database name (``harp:harp@.../harp``). Masking each
occurrence of it corrupted the message and swapped the exception type, so ``harp-proxy server`` lost the
clean outdated-schema panel and its ``harp-proxy db:migrate`` command.
"""

import asyncio
from contextlib import asynccontextmanager
from functools import partial

import pytest
from pydantic_core import MultiHostUrl
from sqlalchemy import URL, make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from harp.commandline.system import config_subcommand
from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.errors import OutdatedSchemaError
from harp.utils.testing.cli import CliRunner
from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.utils.migrations import StorageBootError, hide_password, mask_failure, printable_url

# Passwords that also read as free text: the user name, a common word, a single character.
WORD_LIKE = [("harp", "harp"), ("user", "password"), ("u", "1"), ("app_user", "app_user")]


def _url(username, password, *, database="harp", **query):
    return URL.create(
        "postgresql+asyncpg",
        username=username,
        password=password,
        host="127.0.0.1",
        port=55432,
        database=database,
        query=query,
    )


@pytest.mark.parametrize("username, password", WORD_LIKE)
def test_hide_password_leaves_the_rest_of_the_message_intact(username, password):
    url = _url(username, password)
    shown = url.render_as_string(hide_password=False)
    template = (
        "harp.errors.OutdatedSchemaError: The storage schema of {} is outdated (at revision none).\n"
        "  - migrate it: harp-proxy db:migrate up heads --set storage.url={}\n"
        "config: {}; driver: password authentication failed for user {!r}\n"
        "another url: redis://{}:{}@cache/0?password={}"
    )

    masked = hide_password(
        template.format(shown, MultiHostUrl(shown), shown.replace("%", "%%"), username, username, password, password),
        url,
    )

    hidden = url.render_as_string(hide_password=True)
    assert masked == template.format(hidden, hidden, hidden, username, username, "***", "***")


@pytest.mark.parametrize("password", ["Top@Secret", "sp ace%x", "harp", "1"])
def test_hide_password_masks_a_query_password(password):
    url = URL.create(
        "postgresql+asyncpg",
        username="harp",
        host="db",
        database="harp",
        query={"password": password, "ssl": "disable"},
    )
    shown = url.render_as_string(hide_password=False)

    masked = hide_password(f"bad {shown}; settings {MultiHostUrl(shown)}; config {shown.replace('%', '%%')}", url)

    hidden = "postgresql+asyncpg://harp@db/harp?password=***&ssl=disable"
    assert masked == f"bad {hidden}; settings {hidden}; config {hidden}"


def test_printable_url_masks_the_userinfo_and_the_query_password():
    url = make_url("postgresql+asyncpg://harp:harp@db/harp?password=Top%40Secret&ssl=disable")

    assert printable_url(url) == "postgresql+asyncpg://harp:***@db/harp?password=***&ssl=disable"


@pytest.mark.parametrize("username, password", WORD_LIKE)
def test_a_failure_without_the_password_in_a_url_is_kept_as_is(username, password):
    url = _url(username, password)
    for exc in (
        OutdatedSchemaError(f"The storage schema of {printable_url(url)} is outdated: harp-proxy db:migrate up head"),
        ConnectionError(f'password authentication failed for user "{username}"'),
    ):
        assert mask_failure(exc, url) is exc


@asynccontextmanager
async def _database_owned_by(database_url, username, password):
    """An empty database, owned by a login role with the given password, on the test container."""
    admin = create_async_engine(database_url)
    async with admin.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(f"""CREATE ROLE "{username}" LOGIN PASSWORD '{password}'"""))
        await conn.execute(text(f'CREATE DATABASE "{username}" OWNER "{username}"'))
    try:
        yield make_url(database_url).set(username=username, password=password, database=username)
    finally:
        async with admin.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text(f'DROP DATABASE "{username}" WITH (FORCE)'))
            await conn.execute(text(f'DROP ROLE "{username}"'))
        await admin.dispose()


async def _boot(url: str, **storage):
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": url, **storage}, "proxy": {}})
    config = builder.build()
    system = await SystemBuilder(builder.applications, config).abuild()
    await system.dispose()


@parametrize_with_database_urls("postgresql")
@pytest.mark.parametrize("username, password", WORD_LIKE)
async def test_an_outdated_schema_is_refused_with_a_usable_command(database_url, username, password):
    async with _database_owned_by(database_url, username, password) as url:
        with pytest.raises(OutdatedSchemaError) as exc_info:
            await _boot(url.render_as_string(hide_password=False), migrate=False)

    message = str(exc_info.value)
    hidden = url.render_as_string(hide_password=True)
    assert f"The storage schema of {hidden} is outdated" in message
    assert f"harp-proxy db:migrate up heads --set storage.url={hidden}\n" in message
    assert url.render_as_string(hide_password=False) not in message


@parametrize_with_database_urls("postgresql")
@pytest.mark.parametrize("username, password", [("user", "password"), ("app_user", "app_user")])
async def test_a_wrong_password_keeps_the_driver_error(database_url, username, password):
    async with _database_owned_by(database_url, username, "other") as url:
        with pytest.raises(Exception) as exc_info:
            await _boot(url.set(password=password).render_as_string(hide_password=False), migrate=False)

    assert not isinstance(exc_info.value, StorageBootError)
    assert f'password authentication failed for user "{username}"' in str(exc_info.value)


QUERY_PASSWORD = "Qu3ry@Secret"


def _with_query_password(url: URL) -> str:
    url = URL.create(
        url.drivername,
        username=url.username,
        host=url.host,
        port=url.port,
        database=url.database,
        query={"password": QUERY_PASSWORD},
    )
    return url.render_as_string(hide_password=False)


@parametrize_with_database_urls("postgresql")
async def test_an_outdated_schema_masks_a_query_password(database_url):
    async with _database_owned_by(database_url, "harp_query", QUERY_PASSWORD) as url:
        with pytest.raises(OutdatedSchemaError) as exc_info:
            await _boot(_with_query_password(url), migrate=False)

    message = str(exc_info.value)
    assert "?password=***" in message
    assert "Qu3ry" not in message


@parametrize_with_database_urls("postgresql")
@pytest.mark.parametrize("options", [[], ["--raw"], ["--json"]])
async def test_system_config_masks_a_query_password(database_url, options, tmp_path):
    async with _database_owned_by(database_url, "harp_query", QUERY_PASSWORD) as url:
        path = tmp_path / "harp.yml"
        path.write_text(
            f"applications: [http_client, proxy, storage]\nstorage:\n  url: '{_with_query_password(url)}'\n"
        )

        # the command runs its own event loop
        invoke = partial(CliRunner().invoke, config_subcommand, [*options, "--file", str(path)], env={"COLUMNS": "500"})
        result = await asyncio.get_running_loop().run_in_executor(None, invoke)

    assert result.exit_code == 0, result.output
    assert "password=***" in result.output
    assert "Qu3ry" not in result.output


@pytest.mark.parametrize(
    "written",
    [
        "postgresql://u:Zq9!b%24@db/harp",  # partially encoded
        "postgresql://u:Zq9%21b%2f%3a@db/harp",  # lowercase hex
        "postgresql://u:Zq9%%21b@db/harp",  # configparser doubling
        "postgresql://u@db/harp?password=Zq9%2fb&ssl=disable",
    ],
)
def test_hide_password_masks_a_url_whatever_its_encoding(written):
    masked = hide_password(f"boom {written}!", "postgresql://u:Zq9!b@db/harp")

    assert "Zq9" not in masked
    assert "***" in masked


MULTI_HOST_URL = "postgresql+asyncpg://u:Zq9!b%24@127.0.0.1:1,127.0.0.1:2/harp"


def test_mask_failure_masks_a_url_sqlalchemy_cannot_parse():
    safe = mask_failure(ValueError(f"cannot connect to {MULTI_HOST_URL}"), MULTI_HOST_URL)

    assert isinstance(safe, StorageBootError)
    assert "Zq9" not in str(safe)
    assert "u:***@127.0.0.1:1,127.0.0.1:2/harp" in str(safe)


def test_a_password_with_spaces_is_masked_in_the_storage_url():
    url = _url("u", "sp ace x")
    shown = url.render_as_string(hide_password=False)

    assert hide_password(f"boom {shown}!", url) == f"boom {url.render_as_string(hide_password=True)}!"
