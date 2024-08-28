from typing import Any


def import_string(type: str) -> Any:
    _path, _attr = type.rsplit(".", 1)
    concrete_type = getattr(__import__(_path, fromlist=[_attr]), _attr)
    return concrete_type
