import importlib.util
from typing import TYPE_CHECKING

from .defaults import DEFAULT_NAMESPACES

if TYPE_CHECKING:
    from .applications import Application


def resolve_application_name(spec):
    if "." not in spec:
        for namespace in DEFAULT_NAMESPACES:
            _candidate = ".".join((namespace, spec))
            if importlib.util.find_spec(_candidate):
                return _candidate

    if importlib.util.find_spec(spec):
        return spec

    raise ModuleNotFoundError(f"No application named {spec}.")


#: Cache for applications
_applications = {}


def get_application(name: str) -> "Application":
    """
    Returns the application class for the given application name.

    todo: add name/full_name attributes with raise if already set to different value ?

    :param name:
    :return:
    """
    name = resolve_application_name(name)

    if name not in _applications:
        application_spec = importlib.util.find_spec(name)
        if not application_spec:
            raise ValueError(f'Unable to find application "{name}".')

        try:
            application_module = __import__(".".join((application_spec.name, "__app__")), fromlist=["*"])
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                f'A python package for application "{name}" was found but it is not a valid harp application. '
                'Did you forget to add an "__app__.py"?'
            ) from exc

        if not hasattr(application_module, "application"):
            raise AttributeError(f'Application module for {name} does not contain a "application" attribute.')

        _applications[application_spec.name] = getattr(application_module, "application")

    if name not in _applications:
        raise RuntimeError(f'Unable to load application "{name}", application class definition not found.')

    return _applications[name]
