"""
The Config (:mod:`harp.config`) module provides tools to configure *Applications*.

*Applications* are standard python packages that contains specific definitions to be able to register services and
configure themselves. Every feature of Harp is built as an application, and you will want to write applications if you
want to extend harp's functionality for specific needs.


Contents
--------

"""

__title__ = "Config"

from .applications import Application, ApplicationsRegistry
from .builders import ConfigurationBuilder, System, SystemBuilder
from .events import (
    EVENT_BIND,
    EVENT_BOUND,
    EVENT_READY,
    EVENT_SHUTDOWN,
    OnBindEvent,
    OnBoundEvent,
    OnReadyEvent,
    OnShutdownEvent,
)
from .settings import (
    Definition,
    DisableableBaseSettings,
    DisabledSettings,
    FromFileSetting,
    Lazy,
    Settings,
    asdict,
    settings_dataclass,
)
from .utils import get_application

__all__ = [
    "Application",
    "ApplicationsRegistry",
    "ConfigurationBuilder",
    "Definition",
    "DisableableBaseSettings",
    "DisabledSettings",
    "EVENT_BIND",
    "EVENT_BOUND",
    "EVENT_READY",
    "EVENT_SHUTDOWN",
    "FromFileSetting",
    "Lazy",
    "OnBindEvent",
    "OnBoundEvent",
    "OnReadyEvent",
    "OnShutdownEvent",
    "Settings",
    "System",
    "SystemBuilder",
    "asdict",
    "get_application",
    "settings_dataclass",
]
