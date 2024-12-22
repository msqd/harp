import os.path
from importlib import import_module

from yaml import Node, ScalarNode, SequenceNode, add_constructor
from yaml import dump as yaml_dump
from yaml import load as yaml_load
from yaml import safe_load as yaml_safe_load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader

from yaml import SafeLoader


def load(filename, *, Loader=Loader):
    with open(filename) as f:
        return yaml_load(f, Loader=Loader)


safe_load = yaml_safe_load


def dump(data, stream=None, **kwargs):
    return yaml_dump(data, stream, Dumper=Dumper, **kwargs)


def _include(filename):
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        return load(filename, Loader=Loader)
    if filename.endswith(".py"):
        with open(filename) as f:
            return f.read()
    raise ValueError(f"Unknown file extension in yaml include: {filename}")


def include_constructor(self, node):
    filename = self.construct_scalar(node)

    if " from " in filename:
        filename, module = filename.split(" from ")
        module = import_module(module)
        for _path in module.__path__:
            filename = os.path.join(_path, filename)
            if os.path.exists(filename):
                return _include(filename)
        raise FileNotFoundError(f"File not found: {filename} (search path: {', '.join(module.__path__)})")

    return _include(filename)


add_constructor("!include", include_constructor, Loader=Loader)
add_constructor("!include", include_constructor, Loader=SafeLoader)

__all__ = [
    "Node",
    "ScalarNode",
    "SequenceNode",
    "Dumper",
    "Loader",
    "add_constructor",
    "dump",
    "load",
    "safe_load",
]
