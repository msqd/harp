import asyncio
from concurrent.futures import ThreadPoolExecutor

from click.testing import CliRunner
from sqlalchemy import text

from harp.commandline import migrations


async def run_migrations(database_url, /, *, operation="up", revision="head"):
    def _migrate():
        cli = CliRunner()
        return cli.invoke(migrations.migrate, [operation, revision, "--set", "storage.url=" + database_url])

    with ThreadPoolExecutor() as executor:
        result = await asyncio.get_event_loop().run_in_executor(executor, _migrate)

    return result


async def run_sql(engine, sql, *, autocommit=True):
    if isinstance(sql, str):
        sql = text(sql)
    async with engine.connect() as conn:
        result = await conn.execute(sql)
        if autocommit:
            await conn.commit()
    return result
