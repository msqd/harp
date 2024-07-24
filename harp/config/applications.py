from typing import Type

from rodi import Container
from whistle import IAsyncEventDispatcher

from .events import EVENT_FACTORY_BIND, EVENT_FACTORY_BOUND, EVENT_FACTORY_BUILD, EVENT_FACTORY_DISPOSE
from .settings.base import asdict
from .utils import get_application_type, resolve_application_name


class Application:
    class Settings(dict):
        pass

    class Lifecycle:
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

        on_dispose = None
        """
        Placeholder for factory dispose event, happening after the kernel is disposed. If set, it will be attached to the
        factory dispatcher automatically, in reverse order of appearance (first loaded application will be disposed last).
        """


class ApplicationsRegistry:
    def __init__(self):
        self._applications = {}

    def __contains__(self, name):
        return name in self._applications

    def __getitem__(self, name):
        return self._applications[name]

    def __iter__(self):
        yield from self._applications

    def __len__(self):
        return len(self._applications)

    def get_full_name(self, name):
        mod_name = self[name].__module__
        if mod_name.endswith(".__app__"):
            return mod_name[:-8]
        return mod_name + "." + self[name].__qualname__

    def add(self, *names):
        for name in names:
            full_name = resolve_application_name(name)
            short_name = full_name.split(".")[-1]

            if short_name not in self._applications:
                self._applications[short_name] = get_application_type(full_name)
            elif self._applications[short_name] != get_application_type(full_name):
                raise ValueError(
                    f"Application {short_name} already registered with a different type ({self._applications[short_name].__module__}.{self._applications[short_name].__qualname__})."
                )

    def remove(self, *names):
        for name in names:
            full_name = resolve_application_name(name)
            short_name = full_name.split(".")[-1]

            if short_name in self._applications:
                del self._applications[short_name]

    def items(self):
        return self._applications.items()

    def keys(self):
        return self._applications.keys()

    def values(self):
        return self._applications.values()

    def lifecycle_for(self, name) -> Type[Application.Lifecycle]:
        return getattr(self._applications[name], "Lifecycle") or Application.Lifecycle

    def settings_for(self, name) -> Type[Application.Settings]:
        return getattr(self._applications[name], "Settings") or dict

    def defaults(self):
        return {name: asdict(self.settings_for(name)()) for name in self._applications}

    def register_events(self, dispatcher: IAsyncEventDispatcher):
        for name, AppType in self.items():
            lifecycle = getattr(AppType, "Lifecycle", None) or Application.Lifecycle

            if on_bind := getattr(lifecycle, "on_bind", None):
                dispatcher.add_listener(EVENT_FACTORY_BIND, on_bind)

            if on_bound := getattr(lifecycle, "on_bound", None):
                dispatcher.add_listener(EVENT_FACTORY_BOUND, on_bound)

            if on_build := getattr(lifecycle, "on_build", None):
                dispatcher.add_listener(EVENT_FACTORY_BUILD, on_build)

        for name, AppType in reversed(self.items()):
            lifecycle = getattr(AppType, "Lifecycle", None) or Application.Lifecycle

            if on_dispose := getattr(lifecycle, "on_dispose", None):
                dispatcher.add_listener(EVENT_FACTORY_DISPOSE, on_dispose)

    def register_services(self, container: Container, config: dict):
        for name, AppType in self.items():
            settings_type = self.settings_for(name)
            local_config = config.get(name, None)
            if settings_type is not dict and local_config:
                container.add_instance(local_config, settings_type)

    def aslist(self):
        return [self.get_full_name(name) for name in self]
