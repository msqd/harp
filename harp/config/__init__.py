"""
The Config (:mod:`harp.config`) module provides tools to configure *Applications*.

*Applications* are standard python packages that contains specific definitions to be able to register services and
configure themselves. Every feature of Harp is built as an application, and you will want to write applications if you
want to extend harp's functionality for specific needs.


Contents
--------

"""

__title__ = "Config"

from .application import Application
from .config import Config
from .settings import (
    BaseSetting,
    Definition,
    DisableableBaseSettings,
    DisabledSettings,
    FromFileSetting,
    Lazy,
    asdict,
    settings_dataclass,
)

__all__ = [
    "Application",
    "BaseSetting",
    "Config",
    "Definition",
    "DisableableBaseSettings",
    "DisabledSettings",
    "FromFileSetting",
    "Lazy",
    "asdict",
    "settings_dataclass",
]
