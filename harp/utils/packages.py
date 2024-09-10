from typing import Any


def import_string(type: str) -> Any:
    _path, _attr = type.rsplit(".", 1)
    concrete_type = getattr(__import__(_path, fromlist=[_attr]), _attr)
    return concrete_type


def get_module_name(_type):
    return _type.__module__


def get_qualified_name(_type):
    try:
        return _type.__qualname__
    except AttributeError:
        return _type.__name__


def get_full_qualified_name(_type):
    return f"{get_module_name(_type)}.{get_qualified_name(_type)}"
