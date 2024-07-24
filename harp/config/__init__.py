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
    EVENT_FACTORY_BIND,
    EVENT_FACTORY_BOUND,
    EVENT_FACTORY_BUILD,
    EVENT_FACTORY_DISPOSE,
    FactoryBindEvent,
    FactoryBoundEvent,
    FactoryBuildEvent,
    FactoryDisposeEvent,
)
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
from .utils import get_application_type

__all__ = [
    "Application",
    "ApplicationsRegistry",
    "BaseSetting",
    "ConfigurationBuilder",
    "Definition",
    "DisableableBaseSettings",
    "DisabledSettings",
    "EVENT_FACTORY_BIND",
    "EVENT_FACTORY_BOUND",
    "EVENT_FACTORY_BUILD",
    "EVENT_FACTORY_DISPOSE",
    "FactoryBindEvent",
    "FactoryBoundEvent",
    "FactoryBuildEvent",
    "FactoryDisposeEvent",
    "FromFileSetting",
    "Lazy",
    "System",
    "SystemBuilder",
    "asdict",
    "get_application_type",
    "settings_dataclass",
]
