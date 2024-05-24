from dataclasses import dataclass


def cast_bool(x):
    if isinstance(x, str):
        value = x.lower()
        if value in ("true", "yes", "1"):
            return True
        elif value in ("false", "no", "0"):
            return False
        else:
            raise ValueError(f"Invalid string value: {x}")
    return bool(x)


@dataclass
class SqlAlchemyStorageSettings:
    type: str = "sqlalchemy"
    url: str = "sqlite+aiosqlite:///harp.db"
    drop_tables: bool = False
    echo: bool = False

    def __post_init__(self):
        self.drop_tables = cast_bool(self.drop_tables)
        self.echo = cast_bool(self.echo)
