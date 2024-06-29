from functools import cached_property
from typing import override

from sqlalchemy import make_url
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import create_async_engine

from harp import get_logger

from ..utils.sql import run_sql
from ._base import BaseOptional

logger = get_logger(__name__)


class PgTrgmOptional(BaseOptional):
    """
    Installs or uninstalls the required tools for postrges' trigram based indexes and search.

    """

    def __init__(self, db_url):
        self._url = db_url

    @cached_property
    def engine(self):
        engine = create_async_engine(self.url)

        if engine.dialect.name != "postgresql":
            raise RuntimeError("This optional is only available for PostgreSQL databases.")

        return engine

    @cached_property
    def url(self):
        return make_url(self._url)

    @override
    async def is_supported(self):
        return self.url.get_dialect().name == "postgresql"

    @override
    async def install(self):
        """Install this optional feature in the database. This will install the pg_trgm extension and create optimized
        index for search."""
        is_pg_trm_available = await self._is_pg_trgm_extension_installed()

        if not is_pg_trm_available:
            try:
                await self._install_pg_trgm_extension_if_possible()
                is_pg_trm_available = await self._is_pg_trgm_extension_installed()
            except DatabaseError as e:
                logger.error(f"Failed to install pg_trgm extension: {e}")

        if not is_pg_trm_available:
            logger.error(
                "pg_trgm extension is not available, cannot create optimized indexes, will still create regular one."
            )
        else:
            await self._create_gin_index("messages", "summary")
            await self._create_gin_index("transactions", "endpoint")

    @override
    async def uninstall(self):
        """Remove this optional feature from database. Please note that the extension is not uninstalled, as it may
        have more side effect than we'd like too. Some deeper understanding of what is a PG extension and how scoped
        there are would be great."""
        await self._drop_index("messages", "summary")
        await self._drop_index("transactions", "endpoint")

        if await self._is_pg_trgm_extension_installed():
            logger.warning(
                "pg_trgm extension is installed and wont be removed, if you need to, you can remove it by hand."
            )

    async def _is_pg_trgm_extension_installed(self) -> bool:
        """Check if pg_trgm extension is already installed in the database."""
        result = await self._run_sql("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")
        return result.rowcount > 0

    async def _run_sql(self, sql):
        """Run a SQL statement on the database (via sqlalchemy DBAL engine)."""
        return await run_sql(self.engine, sql)

    async def _install_pg_trgm_extension_if_possible(self):
        """Make sure the pg_trgm extension is installed in the database. This may fail, we'll alert the user about
        that, although there may be good reasons for this to fail (no privilege ...)."""
        try:
            await self._run_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        except DatabaseError as e:
            logger.error(f"Failed to install pg_trgm extension: {e}")

    async def _create_gin_index(self, table_name, column_name):
        """Create a GIN index on a column, using the pg_trgm extension."""
        await self._run_sql(
            f"CREATE INDEX {table_name}_{column_name}_gin ON {table_name} USING gin ({column_name} gin_trgm_ops);"
        )

    async def _drop_index(self, table_name, column_name):
        """Drop an index on a column."""
        await self._run_sql(f"DROP INDEX IF EXISTS {table_name}_{column_name}_gin;")
