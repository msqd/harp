from dataclasses import dataclass
from functools import cached_property
from importlib import import_module
from importlib.util import find_spec
from typing import Any, Generic, Mapping, Optional, Tuple, TypeVar

T = TypeVar("T")


@dataclass(kw_only=True, frozen=True)
class Definition(Generic[T]):
    path: str
    name: str
    args: Optional[Tuple] = None
    kwargs: Optional[Mapping] = None

    @cached_property
    def spec(self):
        return find_spec(self.path)

    @cached_property
    def module(self):
        return import_module(self.path)

    @cached_property
    def factory(self):
        return getattr(self.module, self.name)

    def validate(self):
        # For now, only validate module exists, but we may want to import it to check the existence of the attribute
        # inside. We opted out for now as the import can (but should not) have side effects.
        if not self.spec:
            raise ImportError(f"Module {self.path} not found.")
        return True

    def build(self, *args, **kwargs) -> T:
        return self.factory(*self.args, *args, **self.kwargs, **kwargs)

    def _asdict(self):
        return {
            "@type": ":".join((self.path, self.name)),
            **({"@args": self.args} if len(self.args) else {}),
            **self.kwargs,
        }

    to_dict = _asdict


@dataclass(frozen=True)
class ConstantDefinition(Definition):
    value: Any = None
    path: str = None
    name: str = None

    @cached_property
    def spec(self):
        return None

    @cached_property
    def module(self):
        return None

    @cached_property
    def factory(self):
        return lambda: self.value

    def build(self):
        return self.value

    def _asdict(self):
        return self.value


def Lazy(path_or_factory, *args, _default=None, **kwargs) -> Definition[type]:
    if path_or_factory is None:
        return ConstantDefinition(value=None)

    if isinstance(path_or_factory, Definition):
        return path_or_factory

    if callable(path_or_factory):
        # noinspection PyTypeChecker
        return type(
            path_or_factory.__name__ + "Definition",
            (Definition,),
            {"factory": path_or_factory},
        )(
            path=path_or_factory.__module__,
            name=path_or_factory.__name__,
            args=args,
            kwargs=kwargs,
        )

    if isinstance(path_or_factory, dict):
        path = path_or_factory.pop("@type", _default.factory if _default else None)
        args = path_or_factory.pop("@args", ())
        return Lazy(path, *args, **((_default.kwargs if _default else {}) | path_or_factory))

    if isinstance(path_or_factory, str):
        path, name = path_or_factory.rsplit(":", 1)
        return Definition(path=path, name=name, args=args, kwargs=kwargs)

    raise ValueError(f"Invalid lazy factory definition {repr(path_or_factory)}.")
