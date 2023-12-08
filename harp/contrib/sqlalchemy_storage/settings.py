from dataclasses import dataclass


@dataclass(frozen=True)
class SqlAlchemyStorageSettings:
    type: str = "sqlalchemy"
    url: str = "sqlite+aiosqlite:///harp.db"
    drop_tables: bool = False
    echo: bool = False
