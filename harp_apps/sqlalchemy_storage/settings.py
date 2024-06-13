from dataclasses import dataclass

from harp.utils.env import cast_bool


@dataclass
class SqlAlchemyStorageSettings:
    type: str = "sqlalchemy"
    url: str = "sqlite+aiosqlite:///harp.db"
    migrate: bool = True

    def __post_init__(self):
        self.migrate = cast_bool(self.migrate)
