import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Union

from sqlalchemy import URL, make_url, text
from sqlalchemy.exc import OperationalError

from harp import get_logger
from harp.commandline.options.server import CommonServerOptions
from harp_apps import sqlalchemy_storage
from harp_apps.sqlalchemy_storage.models import Base, Message, Transaction

logger = get_logger(__name__)


def create_alembic_config(url: Union[str, URL]):
    """Create our alembic configuration object, to run alembic commands."""
    from alembic.config import Config as AlembicConfig

    url = make_url(url)

    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", os.path.join(sqlalchemy_storage.__path__[0], "migrations"))
    alembic_cfg.set_main_option(
        "file_template", "%%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s"
    )
    alembic_cfg.set_main_option("truncate_slug_length", "40")
    alembic_cfg.set_main_option("output_encoding", "utf-8")
    alembic_cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    alembic_cfg.set_main_option("configure_logger", "false")

    return alembic_cfg


def create_harp_config_with_sqlalchemy_storage_from_command_line_options(kwargs):
    """Create a Harp configuration object using common server command line options (--set...) with the sqlalchemy
    storage application installed so that the storage is properly configured."""
    from harp import Config as HarpConfig

    options = CommonServerOptions(**kwargs)

    cfg = HarpConfig()
    cfg.add_application("sqlalchemy_storage")
    cfg.read_env(options)
    cfg.validate(allow_extraneous_settings=True)

    return cfg


async def do_migrate(engine, *, migrator, reset=False):
    logger.info(f"🛢 Starting database migrations... (dialect={engine.dialect.name}, reset={reset}).")
    if reset:
        logger.debug("🛢 [db:migrate reset=true] dropping all tables.")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    if engine.dialect.name == "sqlite":
        logger.debug("🛢 [db:migrate dialect=sqlite] creating all tables (without alembic).")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    else:
        # alembic manages migrations except for sqlite, because it's not trivial to make them work and an env using
        # sqlite does not really need to support upgrades (drop/recreate is fine when harp is upgraded).
        logger.debug("🛢 [db:migrate] Running alembic migrations...")

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
