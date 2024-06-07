from dataclasses import asdict, dataclass

from .lazy import Definition, Lazy

settings_dataclass = dataclass


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
