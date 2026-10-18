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
CHUNK_SIZE = 100


async def execute_in_chunks(conn, statement, rows: list[dict], size: int = CHUNK_SIZE) -> None:
    """Executes ``statement`` for ``rows`` a chunk at a time, in the caller's transaction, letting the loop run between."""
    for start in range(0, len(rows), size):
        await conn.execute(statement, rows[start : start + size])
