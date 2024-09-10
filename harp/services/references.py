import operator
import os.path
from importlib import import_module
from typing import Any, Self

from pydantic import BaseModel

from harp.utils.config import yaml


class _NotSet:
    def __repr__(self):
        return "<not set>"


_notset = _NotSet()


class BaseReference(BaseModel):
    """
    Base class for references. Mostly there to add some interface documentation.

    """

    def __init__(self, /, **data: Any) -> None:  # type: ignore
        """Create a new model by parsing and validating input data from keyword arguments.

        Raises :class:`pydantic_core.ValidationError` if the input data cannot be validated.

        """
        super().__init__(**data)

    @classmethod
    def build_from_yaml(cls, loader, node) -> Self:
        """
        Secondary constructor implementing the pyyaml constructor interface.

        """
        raise NotImplementedError("YAML constructor not implemented")


class LazyServiceReference(BaseReference):
    """
    Reference to a service, that will be resolved the latest possible, when the instance will actually be needed.
    """

    #: Reference target, a.k.a. the service symbolic name. Can be either a string, or a list of strings. The later will
    #: resolve as the first available service in the list.
    target: str | list[str]

    @classmethod
    def build_from_yaml(cls, loader, node) -> Self:
        if isinstance(node, yaml.ScalarNode):
            return cls(target=loader.construct_scalar(node))

        elif isinstance(node, yaml.SequenceNode):
            values = loader.construct_sequence(node)
            return cls(target=values)

        raise ValueError(f"Unsupported node type: {type(node)}")

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.target)})"

    def resolve(self, resolver, context):
        """
        Resolve reference value in using the given resolver (callable) and resolution context.
        """
        return resolver(self.target, context)


operators = {
    "==": operator.eq,
    " is not ": operator.is_not,
    " is ": operator.is_,
}


class LazySettingReference(BaseReference):
    """
    Reference to a setting value, that will be resolved when the settings are bound to the service definitions
    collection, when calling :meth:`harp.services.Container.load`.

    Use this in `services.yml` files using the `!cfg` constructor:

    .. code:: yaml

        foo: !cfg "foo"

    Can be provided a two-element list for defaults:

    .. code:: yaml

        foo: !cfg ["foo", "default if no «foo» in bound settings"]

    """

    target: str
    default: Any = _notset

    def __init__(self, target=None, **kwargs):
        super().__init__(target=target, **kwargs)

    @classmethod
    def build_from_yaml(cls, loader, node) -> Self:
        if isinstance(node, yaml.ScalarNode):
            return cls(loader.construct_scalar(node))
        elif isinstance(node, yaml.SequenceNode):
            values = loader.construct_sequence(node)
            assert len(values) == 2
            return cls(values[0], default=values[1])

        raise ValueError(f"Unsupported node type: {type(node)}")

    def resolve(self, settings):
        operator = None
        if "==" in self.target:
            target, operator, other_operand = self.target.partition("==")
        elif " is not " in self.target:
            target, operator, other_operand = self.target.partition(" is not ")
        elif " is " in self.target:
            target, operator, other_operand = self.target.partition(" is ")
        else:
            target = self.target
            other_operand = None

        x = settings
        for part in target.strip().split("."):
            try:
                x = x[part]
            except (TypeError, KeyError):
                x = self.default
                break

        if operator and other_operand:
            other_operand = eval(other_operand.strip())
            if operator in operators:
                return operators[operator](x, other_operand) or None
            else:
                raise ValueError(f"Unsupported operator: {operator}")

        return x if x is not _notset else None

    def __str__(self):
        return f"!cfg {self.target}"


def _include(self, node):
    filename = self.construct_scalar(node)

    if " from " in filename:
        filename, module = filename.split(" from ")
        module = import_module(module)
        for _path in module.__path__:
            filename = os.path.join(_path, filename)
            if os.path.exists(filename):
                return yaml.load(filename, Loader=yaml.Loader)
        raise FileNotFoundError(f"File not found: {filename} (search path: {', '.join(module.__path__)})")

    return yaml.load(filename, Loader=yaml.Loader)


yaml.add_constructor("!ref", LazyServiceReference.build_from_yaml, Loader=yaml.Loader)
yaml.add_constructor("!cfg", LazySettingReference.build_from_yaml, Loader=yaml.Loader)
yaml.add_constructor("!include", _include, Loader=yaml.Loader)
