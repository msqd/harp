import importlib.util
import os
from typing import ItemsView, KeysView, Optional, Type, ValuesView

from whistle import IAsyncEventDispatcher

from harp.services import Container

from .. import get_relative_path
from .asdict import asdict
from .events import (
    EVENT_BIND,
    EVENT_BOUND,
    EVENT_READY,
    EVENT_SHUTDOWN,
    OnBindHandler,
    OnBoundHandler,
    OnReadyHandler,
    OnShutdownHandler,
)

#: Cache for applications
applications = {}


class Application:
    settings_type: Type = None
    """Type definition for configuration parsing."""

    on_bind: OnBindHandler = None
    """Placeholder for factory bind event, happening before the container is built. If set, it will be attached to the
    factory dispatcher automatically."""

    on_bound: OnBoundHandler = None
    """Placeholder for factory bound event, happening after the container is built. If set, it will be attached to the
    factory dispatcher automatically."""

    on_ready: OnReadyHandler = None
    """Placeholder for factory build event, happening after the kernel is built. If set, it will be attached to the
    factory dispatcher automatically."""

    on_shutdown: OnShutdownHandler = None
    """Placeholder for factory dispose event, happening after the kernel is disposed. If set, it will be attached to the
    factory dispatcher automatically, in reverse order of appearance (first loaded application will be disposed last).
    """

    #: A placeholder for the source path of the application.
    path: Optional[str] = None

    def __init__(
        self,
        *,
        on_bind: OnBindHandler = None,
        on_bound: OnBoundHandler = None,
        on_ready: OnReadyHandler = None,
        on_shutdown: OnShutdownHandler = None,
        settings_type: Type = None,
        dependencies: list[str] = None,
    ):
        self.settings_type = settings_type if settings_type is not None else dict
        self.on_bind = on_bind
        self.on_bound = on_bound
        self.on_ready = on_ready
        self.on_shutdown = on_shutdown

        # todo: implement dependencies
        self.dependencies = dependencies or []

    def defaults(self):
        if self.settings_type:
            return asdict(self.settings_type())
        return {}

    def normalize(self, settings):
        if self.settings_type:
            if not isinstance(settings, self.settings_type):
                settings = self.settings_type(**settings)
            return asdict(settings, secure=False)
        return settings

    def has_application_settings_mixin(self):
        """Check if settings_type has ApplicationSettingsMixin in its inheritance chain."""
        if self.settings_type is None or self.settings_type is dict:
            return False
        from .mixins import ApplicationSettingsMixin

        return issubclass(self.settings_type, ApplicationSettingsMixin)


class ApplicationsRegistry:
    namespaces = ["harp_apps"]

    def __init__(self, *, namespaces: Optional[list[str]] = None):
        self._applications = {}
        self.namespaces = namespaces or self.namespaces

    def __contains__(self, name):
        return name in self._applications

    def __getitem__(self, name):
        return self._applications[name]

    def __iter__(self):
        yield from self._applications

    def __len__(self):
        return len(self._applications)

    def resolve_name(self, spec):
        if "." not in spec:
            for namespace in self.namespaces:
                _candidate = ".".join((namespace, spec))
                if importlib.util.find_spec(_candidate):
                    return _candidate

        if importlib.util.find_spec(spec):
            return spec

        raise ModuleNotFoundError(f"No application named {spec}.")

    def get_application(self, name: str) -> "Application":
        """
        Returns the application class for the given application name.

        todo: add name/full_name attributes with raise if already set to different value ?

        :param name:
        :return:
        """
        name = self.resolve_name(name)

        if name not in applications:
            application_spec = importlib.util.find_spec(name)
            if not application_spec:
                raise ValueError(f'Unable to find application "{name}".')

            try:
                application_module = __import__(".".join((application_spec.name, "__app__")), fromlist=["*"])
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    f'A python package for application "{name}" was found but it is not a valid HARP Application. '
                    'Did you forget to add an "__app__.py"?'
                ) from exc

            if not hasattr(application_module, "application"):
                raise AttributeError(f'Application module for {name} does not contain a "application" attribute.')

            applications[application_spec.name] = getattr(application_module, "application")

            try:
                applications[application_spec.name].path = get_relative_path(os.path.dirname(application_spec.origin))
            except TypeError:
                applications[application_spec.name].path = None

        if name not in applications:
            raise RuntimeError(f'Unable to load application "{name}", application class definition not found.')

        return applications[name]

    def resolve_short_name(self, full_name):
        short_name = full_name.split(".")[-1]

        try:
            self.resolve_name(short_name)
            return short_name
        except ModuleNotFoundError:
            return full_name

    def add(self, *names, autoload_dependencies: bool = False):
        """Add applications to the registry.

        Args:
            *names: Application names to add
            autoload_dependencies: If True, automatically add declared dependencies.
                                   Defaults to False for backward compatibility.
        """
        for name in names:
            full_name = self.resolve_name(name)
            short_name = self.resolve_short_name(full_name)

            # If autoload is enabled, load dependencies FIRST
            if autoload_dependencies and short_name not in self._applications:
                app = self.get_application(full_name)
                dependencies = getattr(app, "dependencies", [])
                if dependencies:
                    # Recursively add dependencies before the current app
                    self.add(*dependencies, autoload_dependencies=True)

            if short_name not in self._applications:
                self._applications[short_name] = self.get_application(full_name)
            elif self._applications[short_name] != self.get_application(full_name):
                raise ValueError(
                    f"Application {short_name} already registered with a different type ({self._applications[short_name].__module__}.{self._applications[short_name].__qualname__})."
                )

    def remove(self, *names):
        for name in names:
            full_name = self.resolve_name(name)
            short_name = self.resolve_short_name(full_name)

            if short_name in self._applications:
                del self._applications[short_name]

    def items(self) -> ItemsView[str, Application]:
        return self._applications.items()

    def keys(self) -> KeysView[str]:
        return self._applications.keys()

    def values(self) -> ValuesView[Application]:
        return self._applications.values()

    def defaults(self):
        return {name: self[name].defaults() for name in self._applications}

    def register_events(self, dispatcher: IAsyncEventDispatcher):
        for name, application in self.items():
            if application.on_bind:
                dispatcher.add_listener(EVENT_BIND, application.on_bind)

            if application.on_bound:
                dispatcher.add_listener(EVENT_BOUND, application.on_bound)

            if application.on_ready:
                dispatcher.add_listener(EVENT_READY, application.on_ready)

        for name, application in reversed(self.items()):
            if application.on_shutdown:
                dispatcher.add_listener(EVENT_SHUTDOWN, application.on_shutdown)

    def register_services(self, container: Container, config: dict):
        for name, application in self.items():
            settings_type = self[name].settings_type
            local_config = config.get(name, None)
            if settings_type is not dict and local_config:
                container.add_instance(local_config, settings_type)

    def aslist(self):
        return [self.resolve_name(name) for name in self]

    def validate_dependencies(self):
        """Validate that all declared dependencies exist in the registry."""
        from harp.errors import MissingDependencyError

        for app_name, app in self._applications.items():
            dependencies = getattr(app, "dependencies", [])
            if not dependencies:
                continue

            missing_deps = [dep for dep in dependencies if dep not in self._applications]
            if missing_deps:
                if len(missing_deps) == 1:
                    raise MissingDependencyError(
                        f"Application '{app_name}' requires '{missing_deps[0]}' but it is not enabled"
                    )
                else:
                    raise MissingDependencyError(
                        f"Application '{app_name}' requires {missing_deps} but they are not enabled"
                    )

    def _detect_dependency_cycles(self, graph: dict[str, list[str]]) -> None:
        """Detect circular dependencies using depth-first search.

        Args:
            graph: Dependency graph mapping app names to their dependencies

        Raises:
            CircularDependencyError: If a circular dependency is detected
        """
        from harp.errors import CircularDependencyError

        visited = set()
        recursion_stack = set()

        def has_cycle(node, path):
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in recursion_stack:
                    # Found cycle
                    cycle_start_idx = path.index(neighbor)
                    cycle = path[cycle_start_idx:] + [neighbor]
                    cycle_str = " → ".join(cycle)
                    raise CircularDependencyError(f"Circular dependency detected: {cycle_str}")

            path.pop()
            recursion_stack.remove(node)
            return False

        for app_name in graph:
            if app_name not in visited:
                has_cycle(app_name, [])

    def resolve_dependencies(self):
        """Reorder applications based on dependency order using topological sort."""
        from harp.errors import MissingDependencyError

        # Build dependency graph
        graph = {}
        in_degree = {}
        original_order = list(self._applications.keys())

        for app_name in self._applications:
            graph[app_name] = getattr(self._applications[app_name], "dependencies", [])
            in_degree[app_name] = 0

        # Check for missing dependencies
        for app_name in self._applications:
            for dep in graph[app_name]:
                if dep not in graph:
                    raise MissingDependencyError(f"Application '{app_name}' requires '{dep}' but it is not enabled")

        # Calculate in-degree (number of declared dependencies per app)
        for app_name in self._applications:
            in_degree[app_name] = len(graph[app_name])

        # Detect cycles
        self._detect_dependency_cycles(graph)

        # Topological sort using Kahn's algorithm with stable ordering
        queue = [app_name for app_name in original_order if in_degree[app_name] == 0]
        sorted_apps = []

        while queue:
            node = queue.pop(0)
            sorted_apps.append(node)

            # Find apps that depend on this node
            for app_name in original_order:
                if node in graph[app_name]:
                    in_degree[app_name] -= 1
                    if in_degree[app_name] == 0:
                        queue.append(app_name)

        # Reconstruct _applications dict in sorted order
        self._applications = {name: self._applications[name] for name in sorted_apps}
