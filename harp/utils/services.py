from typing import Callable, Type, TypeVar, cast

T = TypeVar("T")


def factory(t: Type[T]) -> Callable[..., Type[T]]:
    def decorator(f) -> Type[T]:
        return cast(Type[T], type(f.__name__, (t,), {"__new__": f, "__init__": f}))

    return decorator
