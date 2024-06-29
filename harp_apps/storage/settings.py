from dataclasses import asdict, field

from sqlalchemy import URL, make_url

from harp.config import BaseSetting, settings_dataclass
from harp.utils.env import cast_bool


@settings_dataclass
class BlobStorageSettings(BaseSetting):
    type: str = "sql"


@settings_dataclass
class StorageSettings(BaseSetting):
    type: str = "sqlalchemy"
    url: URL = make_url("sqlite+aiosqlite:///harp.db")
    migrate: bool = True
    blobs: BlobStorageSettings = field(default_factory=BlobStorageSettings)

    def __post_init__(self):
        self.migrate = cast_bool(self.migrate)
        self.url = make_url(self.url)

        if isinstance(self.blobs, dict):
            self.blobs = BlobStorageSettings(**self.blobs)

    def _asdict(self, /, *, secure=True):
        return {
            "type": self.type,
            "url": self.url.render_as_string(hide_password=secure),
            "migrate": self.migrate,
            "blobs": asdict(self.blobs),
        }
