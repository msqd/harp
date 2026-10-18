import os.path
from importlib import import_module

from config.yaml import YAMLFile as _BaseYAMLFile
from yaml import Node, ScalarNode, SequenceNode
from yaml import dump as yaml_dump
from yaml import load as yaml_load
from yaml import safe_load as yaml_safe_load

try:
    from yaml import CDumper as Dumper
    from yaml import CSafeLoader as _BaseLoader
except ImportError:
    from yaml import Dumper
    from yaml import SafeLoader as _BaseLoader


class Loader(_BaseLoader):
    """
    HARP's own safe loader. Tags (``!include``, ``!ref``, ``!cfg``) are registered here, never on pyyaml's global
    loaders.
    """


def add_constructor(tag, constructor):
    Loader.add_constructor(tag, constructor)


def load(filename, *, Loader=Loader):
    with open(filename) as f:
        return yaml_load(f, Loader=Loader)


class YAMLFile(_BaseYAMLFile):
    """Configuration source reading yaml files with :class:`Loader`."""

    def read_source(self):
        return load(self.file_path)


safe_load = yaml_safe_load


def dump(data, stream=None, **kwargs):
    return yaml_dump(data, stream, Dumper=Dumper, **kwargs)


def _include(filename, loader_class=Loader):
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        return load(filename, Loader=loader_class)
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
                return _include(filename, type(self))
        raise FileNotFoundError(f"File not found: {filename} (search path: {', '.join(module.__path__)})")

    return _include(filename, type(self))


add_constructor("!include", include_constructor)

__all__ = [
    "Node",
    "ScalarNode",
    "SequenceNode",
    "Dumper",
    "Loader",
    "YAMLFile",
    "add_constructor",
    "dump",
    "load",
    "safe_load",
]
