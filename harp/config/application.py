from dataclasses import is_dataclass
from typing import Optional

from rodi import Container
from whistle import IAsyncEventDispatcher

from .events import EVENT_FACTORY_BIND, EVENT_FACTORY_BOUND, EVENT_FACTORY_BUILD
from .settings import asdict


class Application:
    """
    Base class for writing harp applications, which are basically python packages with auto-registration superpowers.

    TODO:
    - use settings instead of settings_type, with type annotation ?
    - namespace instead of settings namespace ? autodetect from settings ?

    """

    name = None

    settings_namespace = None
    settings_type = None

    on_bind = None
    """
    Placeholder for factory bind event, happening before the container is built. If set, it will be attached to the
    factory dispatcher automatically.

    """

    on_bound = None
    """
    Placeholder for factory bound event, happening after the container is built. If set, it will be attached to the
    factory dispatcher automatically.
    """

    on_build = None
    """
    Placeholder for factory build event, happening after the kernel is built. If set, it will be attached to the
    factory dispatcher automatically.
    """

    def __init__(self, settings=None, /):
        settings = settings or {}
        if isinstance(settings, dict) and self.settings_type is not None:
            settings = self.settings_type(**settings)
        self.settings = settings

    @staticmethod
    def defaults(settings: Optional[dict] = None) -> dict:
        settings = settings if settings is not None else {}
        return settings

    @classmethod
    def supports(cls, settings: dict) -> bool:
        return True

    def validate(self):
        if is_dataclass(self.settings):
            return asdict(self.settings)
        return self.settings

    def register_events(self, dispatcher: IAsyncEventDispatcher):
        if self.on_bind is not None:
            dispatcher.add_listener(EVENT_FACTORY_BIND, self.on_bind)
        if self.on_bound is not None:
            dispatcher.add_listener(EVENT_FACTORY_BOUND, self.on_bound)
        if self.on_build is not None:
            dispatcher.add_listener(EVENT_FACTORY_BUILD, self.on_build)

    def register_services(self, container: Container):
        if self.settings and self.settings_type:
            container.add_instance(self.settings, self.settings_type)

    def __repr__(self):
        return f'<{type(self).__name__} name="{self.name}">'
