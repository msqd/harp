import asyncio
import os
import re
import traceback
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path
from typing import Union
from urllib.parse import quote, quote_plus

from pydantic_core import MultiHostUrl, Url
from sqlalchemy import URL, inspect, make_url, text
from sqlalchemy.exc import OperationalError

from harp import get_logger
from harp.config import ConfigurationBuilder
from harp.config.asdict import mask_credentials
from harp.errors import OutdatedSchemaError
from harp_apps import storage
from harp_apps.storage.models import Base, Message, Transaction

logger = get_logger(__name__)


AnyUrl = Union[str, URL, Url, MultiHostUrl]


def _as_sqlalchemy_url(url: AnyUrl) -> URL:
    return make_url(url if isinstance(url, URL) else str(url))


def _passwords(url: URL) -> list[str]:
    """The password of ``url``, from its userinfo and from a ``?password=`` query parameter (asyncpg reads both)."""
    query = url.query.get("password", ())
    return [password for password in (url.password, *((query,) if isinstance(query, str) else query)) if password]


def _forms(password: str) -> set[str]:
    """Every way ``password`` can be written in a rendered url."""
    forms = {password, quote(password, safe=""), quote(password), quote_plus(password)}
    # SQLAlchemy only escapes the characters that would end the userinfo
    forms.add(URL.create("x", username="", password=password).render_as_string(hide_password=False)[len("x://:") : -1])
    forms |= {re.sub(r"%[0-9A-F]{2}", lambda m: m.group().lower(), form) for form in forms}
    # the form given to configparser doubles every percent sign
    return forms | {form.replace("%", "%%") for form in forms}


def _url_scoped_patterns(url: URL) -> list[re.Pattern]:
    forms = sorted({form for password in _passwords(url) for form in _forms(password)}, key=len, reverse=True)
    alternatives = "|".join(map(re.escape, forms))
    return [
        re.compile(rf"(://[^:/@\s]*:)(?:{alternatives})(?=@)"),
        re.compile(rf"([?&]password=)(?:{alternatives})(?![\w%+.~*-])"),
    ]


def hide_password(message: str, url: AnyUrl) -> str:
    """Mask the password of ``url`` where it sits in a url in ``message``: its userinfo or ``?password=``.

    The shared shape-based masking runs on top, so any other url is covered whatever its encoding. Elsewhere the
    password is left alone: it is often a common word, or the user or database name, and masking it there would
    corrupt the message.
    """
    try:
        patterns = _url_scoped_patterns(_as_sqlalchemy_url(url))
    except Exception:
        # a url SQLAlchemy cannot parse (multi-host): only the shape-based masking applies
        patterns = []
    for pattern in patterns:
        message = pattern.sub(r"\1***", message)
    return mask_credentials(message)


def printable_url(url: AnyUrl) -> str:
    """Render ``url`` for a message, its password masked wherever the url holds it."""
    return mask_credentials(_as_sqlalchemy_url(url).render_as_string(hide_password=True))


class StorageBootError(RuntimeError):
    """A storage failure whose message is the password-masked rendering of the original failure chain."""


def render_failure(exc: BaseException, url: AnyUrl) -> str:
    """Render ``exc`` and its whole cause chain (any attribute ``str()`` uses), password masked."""
    return hide_password("".join(traceback.format_exception(exc, limit=0)).strip(), url)


def mask_failure(exc: BaseException, url: AnyUrl) -> BaseException:
    """Return ``exc`` itself when its rendering holds no password, else a :class:`StorageBootError` that replaces it."""
    raw = "".join(traceback.format_exception(exc, limit=0)).strip()
    masked = render_failure(exc, url)
    if masked == raw:
        return exc
    return StorageBootError(masked).with_traceback(exc.__traceback__)


STORAGE = "storage"


def discover_migration_locations(root: Union[str, Path, None] = None) -> dict[str, Path]:
    """
    Map every application that has a ``migrations/versions`` folder to that folder. The list is static: it does not
    depend on which applications are enabled, so a database migrated while an application was enabled still resolves
    that application's revisions once it is disabled (see ADR-0012).
    """
    import harp_apps

    root = Path(root if root is not None else harp_apps.__path__[0])
    return {path.parent.parent.name: path for path in sorted(root.glob("*/migrations/versions")) if path.is_dir()}


def table_belongs_to(application: str, table_name: str, applications) -> bool:
    """
    Tell if ``application`` owns the table named ``table_name``. An application owns the tables prefixed with its name
    (``auth_users`` for ``auth``). Storage owns what no other application claims, as its tables predate the convention
    (``transactions``, ``messages``, ``blobs``...). When prefixes overlap (``cache`` and ``cache_index``), the longest
    one wins.
    """
    return table_owner(table_name, applications) == application


def table_owner(table_name: str, applications) -> str:
    claims = [other for other in applications if other != STORAGE and table_name.startswith(f"{other}_")]
    return max(claims, key=len, default=STORAGE)


def model_tables() -> list[tuple[str, str]]:
    """``(module, table name)`` of every mapped model."""
    return [(mapper.class_.__module__, mapper.local_table.name) for mapper in Base.registry.mappers]


def check_prefixes(application: str, tables, applications) -> None:
    """
    Refuse to autogenerate for ``application`` when one of its models (``harp_apps.<application>...``) defines a table
    without its prefix: it would silently end up in storage's revisions instead.
    """
    if application == STORAGE:
        return
    stray = sorted(
        name
        for module, name in tables
        if module.split(".")[:2] == ["harp_apps", application] and table_owner(name, applications) != application
    )
    if stray:
        raise ValueError(
            f"Tables of {application!r} must be prefixed {application + '_'!r}, got: {', '.join(stray)}. "
            "Unprefixed tables belong to storage."
        )


def create_alembic_config(url: Union[str, URL, Url, MultiHostUrl], *, locations: Union[dict[str, Path], None] = None):
    """Create our alembic configuration object, to run alembic commands.

    The ``locations`` of all applications (default: discovered under ``harp_apps``) are listed as version locations of
    one alembic environment, enabled or not.
    """
    from alembic.config import Config as AlembicConfig

    if isinstance(url, (Url, MultiHostUrl)):
        url = str(url)

    url = make_url(url)
    locations = discover_migration_locations() if locations is None else locations

    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", os.path.join(storage.__path__[0], "migrations"))
    alembic_cfg.set_main_option("path_separator", "os")
    alembic_cfg.set_main_option(
        "version_locations", os.pathsep.join(str(path).replace("%", "%%") for path in locations.values())
    )
    alembic_cfg.attributes["locations"] = dict(locations)
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


def create_revision(alembic_cfg, application: str, message: str):
    """Autogenerate a revision holding only ``application``'s tables, in its branch (opened if it has none yet)."""
    from alembic import command
    from alembic.script import ScriptDirectory

    locations = alembic_cfg.attributes["locations"]
    if application not in locations:
        raise ValueError(f"Unknown application {application!r}, expected one of: {', '.join(sorted(locations))}.")

    # the models register on Base when imported; an application that is not enabled has not been
    with suppress(ModuleNotFoundError):
        import_module(f"harp_apps.{application}.models")

    check_prefixes(application, model_tables(), locations)
    alembic_cfg.attributes["application"] = application
    revisions = ScriptDirectory.from_config(alembic_cfg).walk_revisions()
    has_branch = any(application in (revision.branch_labels or ()) for revision in revisions)
    command.revision(
        alembic_cfg,
        message=message or "auto-generated migration",
        autogenerate=True,
        version_path=str(locations[application]),
        head=f"{application}@head" if has_branch else "base",
        branch_label=None if has_branch else application,
    )


def current_revisions_by_application(sync_conn, alembic_cfg) -> dict[str, Union[str, None]]:
    """The revision each application's branch is at in the database (``None``: not migrated yet)."""
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_cfg)
    by_folder = {Path(path).resolve(): name for name, path in alembic_cfg.attributes["locations"].items()}
    current: dict[str, Union[str, None]] = {name: None for name in by_folder.values()}
    for revision in MigrationContext.configure(sync_conn).get_current_heads():
        try:
            current[by_folder[Path(script.get_revision(revision).path).resolve().parent]] = revision
        except Exception:
            raise UnknownRevisionError(
                f"The database is at revision {revision!r}, which this version of HARP does not know. It was probably "
                "migrated by a newer version, or by an application whose migrations are not installed."
            ) from None
    return current


class UnknownRevisionError(ValueError):
    """The database holds a revision that no listed migrations folder defines."""


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
        message = render_failure(e, engine.url)
        logger.error(f"🛢 [db:migrate] Migrations failed: {message}")
        raise RuntimeError(f"Could not run migrations ({message}).").with_traceback(e.__traceback__) from None


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


async def ensure_schema_is_current(engine, *, alembic_cfg=None):
    """
    Raise :class:`OutdatedSchemaError` if the database schema is older than what this code expects.

    SQLite schemas are created without alembic, so they are compared to the models. Other databases are compared to
    the latest alembic revision.
    """
    url = engine.url
    shown = printable_url(url)

    if engine.dialect.name == "sqlite":
        async with engine.connect() as conn:
            missing = await conn.run_sync(_missing_columns)
        if not missing:
            return
        details = "missing: " + ", ".join(missing)
        database = url.database
        options = (
            f"  - delete the file, it will be recreated on next start: rm {database}\n"
            f"  - or reset it: harp-proxy db:reset --set storage.url={shown}"
        )
    else:
        alembic_cfg = alembic_cfg or create_alembic_config(url.render_as_string(hide_password=False))
        async with engine.connect() as conn:
            current, head = await conn.run_sync(_alembic_revisions, alembic_cfg)
        if current == head:
            return
        details = f"at revision {', '.join(sorted(current)) or 'none'}, expected {', '.join(sorted(head))}"
        options = (
            f"  - migrate it: harp-proxy db:migrate up heads --set storage.url={shown}\n"
            "  - or let HARP migrate on start: set storage.migrate to true"
        )
        database = shown

    raise OutdatedSchemaError(
        f"The storage schema of {database} is outdated ({details}).\nHARP refuses to start on it. Options:\n{options}"
    )
