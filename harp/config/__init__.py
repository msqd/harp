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
from .asdict import asdict
from .builders import ConfigurationBuilder
from .configurables import Configurable, LazyService, Service, Stateful
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

__all__ = [
    "Application",
    "ApplicationsRegistry",
    "Configurable",
    "ConfigurationBuilder",
    "EVENT_BIND",
    "EVENT_BOUND",
    "EVENT_READY",
    "EVENT_SHUTDOWN",
    "LazyService",
    "OnBindEvent",
    "OnBoundEvent",
    "OnReadyEvent",
    "OnShutdownEvent",
    "Service",
    "Stateful",
    "asdict",
]
