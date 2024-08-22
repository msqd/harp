import operator
from typing import Any, Self

from pydantic import BaseModel

from harp.utils.config import yaml


class _NotSet:
    def __repr__(self):
        return "<not set>"


_notset = _NotSet()


class Reference(BaseModel):
    target: str | list[str]

    @classmethod
    def _yaml_construct(cls, loader, node):
        if isinstance(node, yaml.ScalarNode):
            return cls(target=loader.construct_scalar(node))

        elif isinstance(node, yaml.SequenceNode):
            values = loader.construct_sequence(node)
            return cls(target=values)

        raise ValueError(f"Unsupported node type: {type(node)}")

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.target)})"

    def resolve(self, resolver, context):
        return resolver(self.target, context)


operators = {
    "==": operator.eq,
    " is not ": operator.is_not,
    " is ": operator.is_,
}


class SettingReference(BaseModel):
    target: str
    default: Any = _notset

    def __init__(self, target=None, **kwargs):
        super().__init__(target=target, **kwargs)

    @classmethod
    def _yaml_construct(cls, loader, node) -> Self:
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


yaml.add_constructor("!ref", Reference._yaml_construct, Loader=yaml.Loader)
yaml.add_constructor("!cfg", SettingReference._yaml_construct, Loader=yaml.Loader)
