import asyncio
import importlib
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import cast

from alembic import command
from alembic.config import Config as AlembicConfig
from click import BaseCommand
from pyheck import upper_camel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from harp import get_logger
from harp.commandline.options.server import CommonServerOptions, add_harp_server_click_options
from harp.utils.commandline import click
from harp_apps.sqlalchemy_storage.models import Base, Message, Transaction

logger = get_logger(__name__)


def create_alembic_config(db_url):
    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", "harp_apps/sqlalchemy_storage/migrations")
    alembic_cfg.set_main_option(
        "file_template", "%%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s"
    )
    alembic_cfg.set_main_option("truncate_slug_length", "40")
    alembic_cfg.set_main_option("output_encoding", "utf-8")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("configure_logger", "false")
    return alembic_cfg


def create_harp_config_from_command_line_options(kwargs):
    from harp import Config as HarpConfig

    options = CommonServerOptions(**kwargs)

    cfg = HarpConfig()
    cfg.add_application("sqlalchemy_storage")
    cfg.read_env(options)
    cfg.validate(allow_extraneous_settings=True)
    return cfg


async def do_migrate(engine, *, migrator, reset=False):
    logger.info(f"[db:migrate] Begin (dialect={engine.dialect.name}, reset={reset}).")
    if reset:
        logger.info("[db:migrate reset=true] dropping all tables.")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    if engine.dialect.name == "sqlite":
        logger.info("[db:migrate dialect=sqlite] creating all tables (without alembic).")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    else:
        # alembic manages migrations except for sqlite, because it's not trivial to make them work and an env using
        # sqlite does not really need to support upgrades (drop/recreate is fine when harp is upgraded).
        logger.info("[db:migrate] Running alembic migrations...")

        with ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, migrator)

    if engine.dialect.name == "mysql":
        logger.info("[db:migrate dialect=mysql] creating fulltext indexes.")

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

    logger.info("[db:migrate] Done.")


@click.command()
@add_harp_server_click_options
@click.option("--reset", is_flag=True, help="Reset the database (drop all before migrations).")
def upgrade(*, reset=False, **kwargs):
    config = create_harp_config_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(config.settings.get("storage", {}).get("url", None))
    engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    migrator = partial(command.upgrade, alembic_cfg, "head")
    asyncio.run(do_migrate(engine, migrator=migrator, reset=reset))


upgrade = cast(BaseCommand, upgrade)


@click.command()
@add_harp_server_click_options
def create_migration(**kwargs):
    config = create_harp_config_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(config.settings.get("storage", {}).get("url", None))
    command.revision(alembic_cfg, autogenerate=True, message="auto-generated migration")


@click.command()
@click.argument("operation", nargs=1, type=click.Choice(["add", "remove"]))
@click.argument("features", nargs=-1)
@add_harp_server_click_options
def install_feature(features, operation, **kwargs):
    config = create_harp_config_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(config.settings.get("storage", {}).get("url", None))

    implementations = {}
    for feature in features:
        _module = importlib.import_module(f"harp_apps.sqlalchemy_storage.optionals.{feature}")
        implementations[feature] = getattr(_module, upper_camel(feature + "_optional"))(
            alembic_cfg.get_main_option("sqlalchemy.url")
        )

    for feature in features:
        if operation == "add":
            asyncio.run(implementations[feature].upgrade())
        elif operation == "remove":
            asyncio.run(implementations[feature].downgrade())
        else:
            raise ValueError(f"Invalid operation {operation}.")
