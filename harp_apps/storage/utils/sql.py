from operator import itemgetter

from sqlalchemy import text


async def run_sql(engine, sql, *, autocommit=True):
    if isinstance(sql, str):
        sql = text(sql)
    async with engine.connect() as conn:
        result = await conn.execute(sql)
        if autocommit:
            await conn.commit()
    return result


_get0 = itemgetter(0)


async def run_postgres_explain_analyze(engine, sql):
    return "\n".join(map(_get0, (await run_sql(engine, "EXPLAIN ANALYZE " + sql)).fetchall()))
