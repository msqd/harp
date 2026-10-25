"""
Authentication Application

Accounts, their roles, and the actor a request stands for.
"""

from os.path import dirname
from pathlib import Path

from harp.config import Application, OnBindEvent

from .settings import AuthSettings


async def on_bind(event: OnBindEvent):
    event.container.load(Path(dirname(__file__)) / "services.yml", bind_settings=event.settings["auth"])


application = Application(
    dependencies=["storage"],
    settings_type=AuthSettings,
    on_bind=on_bind,
)
