from os.path import dirname
from pathlib import Path

from harp import get_logger
from harp.config import Application, OnBindEvent

from .settings import HttpClientSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    # Load service definitions, bound to our settings.
    event.container.load(
        Path(dirname(__file__)) / "services.yml",
        bind_settings=event.settings["http_client"],
    )


application = Application(
    on_bind=on_bind,
    settings_type=HttpClientSettings,
)
