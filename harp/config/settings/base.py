import copy
import dataclasses
from dataclasses import dataclass

from .lazy import Definition, Lazy

settings_dataclass = dataclass


def asdict(obj):
    if hasattr(obj, "_asdict"):
        return obj._asdict()

    if type(obj) in dataclasses._ATOMIC_TYPES:
        return obj

    if dataclasses._is_dataclass_instance(obj):
        # fast path for the common case
        return {f.name: asdict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}

    if isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[asdict(v) for v in obj])

    if isinstance(obj, (list, tuple)):
        return type(obj)(asdict(v) for v in obj)

    if isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))
            for k, v in obj.items():
                result[asdict(k)] = asdict(v)
            return result
        return type(obj)((asdict(k), asdict(v)) for k, v in obj.items())

    return copy.deepcopy(obj)


@settings_dataclass
class BaseSetting:
    def to_dict(self):
        return asdict(self)

    def __post_init__(self):
        for _name, _hint in self.__annotations__.items():
            try:
                is_definition = issubclass(_hint, Definition)
            except TypeError:
                is_definition = False

            if hasattr(_hint, "__origin__"):
                try:
                    if issubclass(_hint.__origin__, Definition):
                        is_definition = True
                except TypeError:
                    pass

            if is_definition:
                setattr(self, _name, Lazy(getattr(self, _name), _default=getattr(type(self), _name, None)))
