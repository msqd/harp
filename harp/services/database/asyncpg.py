import asyncpg

_db = None


async def get_connection() -> asyncpg.Connection:
    global _db
    if not _db:
        _db = await asyncpg.connect("postgresql://postgres@localhost/harp")

        _db.execute(
            """
            CREATE TABLE transactions(
                id serial PRIMARY KEY,
                created_at TIMESTAMPZ,
            )
        """
        )

    return _db
