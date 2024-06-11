from functools import cached_property

from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import create_async_engine

from harp import get_logger

logger = get_logger(__name__)


class PgTrgmOptional:
    def __init__(self, db_url, *, echo=False):
        self._url = db_url
        self._echo = echo

    @cached_property
    def engine(self):
        engine = create_async_engine(self._url, echo=self._echo)

        if engine.dialect.name != "postgresql":
            raise RuntimeError("This optional is only available for PostgreSQL databases.")

        return engine

    async def run_sql(self, sql):
        if isinstance(sql, str):
            sql = text(sql)
        async with self.engine.connect() as conn:
            result = await conn.execute(sql)
            await conn.commit()
        return result

    async def is_pg_trgm_extension_installed(self):
        """Check if pg_trgm extension is already installed in the database."""
        result = await self.run_sql("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")
        return result.rowcount > 0

    async def install_pg_trgm_extension_if_possible(self):
        try:
            await self.run_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        except DatabaseError as e:
            logger.error(f"Failed to install pg_trgm extension: {e}")

    async def upgrade(self):
        is_pg_trm_available = await self.is_pg_trgm_extension_installed()

        if not is_pg_trm_available:
            try:
                await self.install_pg_trgm_extension_if_possible()
                is_pg_trm_available = await self.is_pg_trgm_extension_installed()
            except DatabaseError as e:
                logger.error(f"Failed to install pg_trgm extension: {e}")

        if not is_pg_trm_available:
            logger.error(
                "pg_trgm extension is not available, cannot create optimized indexes, will still create regular one."
            )
        else:
            await self.run_sql("CREATE INDEX messages_summary_gin ON messages USING gin (summary gin_trgm_ops);")
            await self.run_sql(
                "CREATE INDEX transactions_endpoint_gin ON transactions USING gin (endpoint gin_trgm_ops);"
            )

        """
        else:
            # Create standard index
            self.engine.execute(text("CREATE INDEX messages_summary_idx ON messages (summary);"))
        """

    async def downgrade(self):
        await self.run_sql("DROP INDEX IF EXISTS messages_summary_gin;")
        await self.run_sql("DROP INDEX IF EXISTS transactions_endpoint_gin;")
        if await self.is_pg_trgm_extension_installed():
            logger.error(
                "pg_trgm extension is installed and wont be removed, if you need to, you can remove it by hand."
            )
