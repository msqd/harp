import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Union

from pydantic_core import MultiHostUrl, Url
from sqlalchemy import URL, inspect, make_url, text
from sqlalchemy.exc import OperationalError

from harp import get_logger
from harp.config import ConfigurationBuilder
from harp.errors import OutdatedSchemaError
from harp_apps import storage
from harp_apps.storage.models import Base, Message, Transaction

logger = get_logger(__name__)


def create_alembic_config(url: Union[str, URL, Url, MultiHostUrl]):
    """Create our alembic configuration object, to run alembic commands."""
    from alembic.config import Config as AlembicConfig

    if isinstance(url, (Url, MultiHostUrl)):
        url = str(url)

    url = make_url(url)

    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", os.path.join(storage.__path__[0], "migrations"))
    alembic_cfg.set_main_option(
        "file_template",
        "%%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s",
    )
    alembic_cfg.set_main_option("truncate_slug_length", "40")
    alembic_cfg.set_main_option("output_encoding", "utf-8")
    # configparser reads `%` as interpolation: escape the percent-encoding SQLAlchemy puts in urls.
    alembic_cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%"))
    alembic_cfg.set_main_option("configure_logger", "false")

    return alembic_cfg


def create_harp_settings_with_storage_from_command_line_options(kwargs):
    """Create a Harp configuration object using common server command line options (--set...) with the sqlalchemy
    storage application installed so that the storage is properly configured."""

    from harp.commandline.options.server import CommonServerOptions

    options = CommonServerOptions(**kwargs)

    builder = ConfigurationBuilder.from_commandline_options(options)
    builder.applications.add("storage")

    return builder.build()


async def do_reset(engine):
    logger.info("🛢 [db:reset] dropping all tables.")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))


async def _do_migrate(engine, *, migrator, reset=False):
    logger.info(f"🛢 Starting database migrations... (dialect={engine.dialect.name}, reset={reset}).")
    if reset:
        await do_reset(engine)

    if engine.dialect.name == "sqlite":
        logger.debug("🛢 [db:migrate dialect=sqlite] creating all tables (without alembic).")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    elif migrator:
        # alembic manages migrations except for sqlite, because it's not trivial to make them work and an env using
        # sqlite does not really need to support upgrades (drop/recreate is fine when harp is upgraded).
        logger.info("🛢 [db:migrate] Running database migrations...")

        with ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, migrator)

    if engine.dialect.name == "mysql":
        logger.debug("🛢 [db:migrate dialect=mysql] creating fulltext indexes.")

        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(f"CREATE FULLTEXT INDEX endpoint_ft_index ON {Transaction.__tablename__} (endpoint);")
                )
                # Create the full text index for messages.summary
                await conn.execute(
                    text(f"CREATE FULLTEXT INDEX summary_ft_index ON {Message.__tablename__} (summary);")
                )
                await conn.commit()
        except OperationalError as e:
            # check for duplicate key error
            if e.orig and e.orig.args[0] == 1061:
                pass
            else:
                raise e

    logger.debug("🛢 [db:migrate] Done.")


async def do_migrate(engine, *, migrator, reset=False):
    try:
        await _do_migrate(engine, migrator=migrator, reset=reset)
    except Exception as e:
        logger.error(f"🛢 [db:migrate] Migrations failed: {e}")
        raise RuntimeError(f"Could not run migrations ({e}).") from e


def _missing_columns(sync_conn) -> list[str]:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    missing = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            missing.append(table.name)
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        missing.extend(f"{table.name}.{column.name}" for column in table.columns if column.name not in existing_columns)
    return missing


def _alembic_revisions(sync_conn, alembic_cfg) -> tuple[set[str], set[str]]:
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    current = set(MigrationContext.configure(sync_conn).get_current_heads())
    head = set(ScriptDirectory.from_config(alembic_cfg).get_heads())
    return current, head


async def ensure_schema_is_current(engine):
    """
    Raise :class:`OutdatedSchemaError` if the database schema is older than what this code expects.

    SQLite schemas are created without alembic, so they are compared to the models. Other databases are compared to
    the latest alembic revision.
    """
    url = engine.url
    printable_url = url.render_as_string(hide_password=True)

    if engine.dialect.name == "sqlite":
        async with engine.connect() as conn:
            missing = await conn.run_sync(_missing_columns)
        if not missing:
            return
        details = "missing: " + ", ".join(missing)
        database = url.database
        options = (
            f"  - delete the file, it will be recreated on next start: rm {database}\n"
            f"  - or reset it: harp-proxy db:reset --set storage.url={printable_url}"
        )
    else:
        alembic_cfg = create_alembic_config(url.render_as_string(hide_password=False))
        async with engine.connect() as conn:
            current, head = await conn.run_sync(_alembic_revisions, alembic_cfg)
        if current == head:
            return
        details = f"at revision {', '.join(sorted(current)) or 'none'}, expected {', '.join(sorted(head))}"
        options = (
            f"  - migrate it: harp-proxy db:migrate up head --set storage.url={printable_url}\n"
            "  - or let HARP migrate on start: set storage.migrate to true"
        )
        database = printable_url

    raise OutdatedSchemaError(
        f"The storage schema of {database} is outdated ({details}).\nHARP refuses to start on it. Options:\n{options}"
    )
