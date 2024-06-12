from sqlalchemy import text


async def run_sql(engine, sql, *, autocommit=True):
    if isinstance(sql, str):
        sql = text(sql)
    async with engine.connect() as conn:
        result = await conn.execute(sql)
        if autocommit:
            await conn.commit()
    return result
