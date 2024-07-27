from dataclasses import field

from sqlalchemy import URL, make_url

from harp.config import Settings, settings_dataclass
from harp.utils.env import cast_bool


@settings_dataclass
class BlobStorageSettings(Settings):
    type: str = "sql"
    url: URL = None

    def __post_init__(self):
        if self.type == "sql":
            if self.url is not None:
                raise ValueError("SQL blob storage does not support custom URLs, it will use the parent storage URL.")

        elif self.type == "redis":
            if self.url is None:
                self.url = make_url("redis://localhost:6379/0")
            elif isinstance(self.url, str):
                self.url = make_url(self.url)

    def _asdict(self, /, *, secure=True):
        return {
            "type": self.type,
            **({"url": self.url.render_as_string(hide_password=secure)} if self.url else {}),
        }


@settings_dataclass
class StorageSettings(Settings):
    url: URL = make_url("sqlite+aiosqlite:///:memory:?cache=shared")
    migrate: bool = True
    blobs: BlobStorageSettings = field(default_factory=BlobStorageSettings)

    def __post_init__(self):
        self.migrate = cast_bool(self.migrate)
        self.url = make_url(self.url)

        if isinstance(self.blobs, dict):
            self.blobs = BlobStorageSettings(**self.blobs)

    def _asdict(self, /, *, secure=True):
        return {
            "url": self.url.render_as_string(hide_password=secure),
            "migrate": self.migrate,
            "blobs": self.blobs._asdict(secure=secure),
        }
