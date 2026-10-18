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
