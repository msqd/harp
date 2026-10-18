import asyncio

from sqlalchemy import insert


def insert_ignoring_duplicates(dialect: str, table, keys: tuple[str, ...] = ("id",)):
    """An insert that leaves rows whose ``keys`` (a unique constraint) already exist alone, on every database."""
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif dialect == "mysql":
        # not IGNORE, which would silently truncate data wider than the column instead of failing
        from sqlalchemy.dialects.mysql import insert as dialect_insert

        return dialect_insert(table).on_duplicate_key_update(**{key: table.c[key] for key in keys})
    else:
        return insert(table)
    return dialect_insert(table).on_conflict_do_nothing(index_elements=list(keys))


#: Rows sent per statement: a batch is one database transaction, but never one long stretch on the event loop.
CHUNK_SIZE = 50


async def execute_in_chunks(conn, statement, rows, size: int | None = None, make_row=None) -> None:
    """
    Executes ``statement`` for ``rows`` a chunk at a time, in the caller's transaction, giving the loop a turn after
    each. ``make_row`` builds the parameters of an item just before its chunk is sent, so no long list is built up front.
    """
    size = size or CHUNK_SIZE
    for start in range(0, len(rows), size):
        chunk = rows[start : start + size]
        await conn.execute(statement, [make_row(row) for row in chunk] if make_row else chunk)
        await asyncio.sleep(0)
