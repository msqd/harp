import importlib.util
from typing import TYPE_CHECKING, Type

from .defaults import DEFAULT_NAMESPACES

if TYPE_CHECKING:
    from .applications import Application


def get_application_class_name(name):
    return "".join(map(lambda x: x.title().replace("_", ""), name.rsplit(".", 1)[-1:])) + "Application"


def resolve_application_name(spec):
    if "." not in spec:
        for namespace in DEFAULT_NAMESPACES:
            _candidate = ".".join((namespace, spec))
            if importlib.util.find_spec(_candidate):
                return _candidate
    if importlib.util.find_spec(spec):
        return spec

    raise ModuleNotFoundError(f"No application named {spec}.")


#: Cache for application types
_application_types = {}


def get_application_type(name: str) -> Type["Application"]:
    """
    Returns the application class for the given application name.

    :param name:
    :return:
    """
    if name not in _application_types:
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

        application_class_name = get_application_class_name(name)
        if not hasattr(application_module, application_class_name):
            raise AttributeError(f'Application module for {name} does not contain a "{application_class_name}" class.')

        _application_types[application_spec.name] = getattr(application_module, application_class_name)
        _application_types[application_spec.name].name = application_spec.name

    if name not in _application_types:
        raise RuntimeError(f'Unable to load application "{name}", application class definition not found.')

    return _application_types[name]
