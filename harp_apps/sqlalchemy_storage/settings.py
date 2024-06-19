from sqlalchemy import URL, make_url

from harp.config import BaseSetting, settings_dataclass
from harp.utils.env import cast_bool


@settings_dataclass
class SqlAlchemyStorageSettings(BaseSetting):
    type: str = "sqlalchemy"
    url: URL = make_url("sqlite+aiosqlite:///harp.db")
    migrate: bool = True

    def __post_init__(self):
        self.migrate = cast_bool(self.migrate)
        self.url = make_url(self.url)

    def _asdict(self, /, *, secure=True):
        return {
            "type": self.type,
            "url": self.url.render_as_string(hide_password=secure),
            "migrate": self.migrate,
        }
