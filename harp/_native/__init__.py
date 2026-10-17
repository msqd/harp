"""
Choice between pure Python and native implementations, driven by the ``HARP_NATIVE`` environment variable.

- unset or ``none``: pure Python everywhere (the reference).
- ``all``: native wherever the extension provides a component, hard failure if the extension is missing.
- ``a,b``: native for the listed components, hard failure if the extension or a listed implementation is missing.

The extension is a module exposing each component under its name, looked up in ``CORE_MODULES`` order:
``harp._native._core`` (built inside harp-proxy) then ``harp_native`` (the ``harp-proxy-native`` distribution).

"""

import os
from importlib import import_module
from types import ModuleType
from typing import Callable

#: Components that may have a native implementation.
COMPONENTS: frozenset[str] = frozenset({"blob_id"})


#: Where the extension may live.
CORE_MODULES = ("harp._native._core", "harp_native")


class NativeUnavailableError(RuntimeError):
    """A native implementation was explicitly requested but cannot be provided."""


def _requested() -> tuple[frozenset[str], bool]:
    """Components asked to be native, and whether every one of them must have a native implementation."""
    value = os.environ.get("HARP_NATIVE", "none").strip()
    if value in ("", "none"):
        return frozenset(), False
    if value == "all":
        return COMPONENTS, False

    names = frozenset(name.strip() for name in value.split(","))
    if unknown := names - COMPONENTS:
        raise ValueError(f"HARP_NATIVE: unknown component(s) {', '.join(sorted(unknown))}.")
    return names, True


def core() -> ModuleType:
    """The extension module, or raise `NativeUnavailableError`."""
    error = None
    for name in CORE_MODULES:
        try:
            return import_module(name)
        except ImportError as exc:
            error = exc
    raise NativeUnavailableError(
        f"HARP_NATIVE requests native code but none of {', '.join(CORE_MODULES)} could be imported."
    ) from error


def _native(component: str) -> Callable | None:
    requested, strict = _requested()
    if component not in requested:
        return None
    impl = getattr(core(), component, None)
    if impl is None and strict:
        raise NativeUnavailableError(f"HARP_NATIVE requests native {component!r} but the extension has none.")
    return impl


def select(component: str, python_impl: Callable) -> Callable:
    """Return the implementation of ``component`` to use, according to ``HARP_NATIVE``."""
    if component not in COMPONENTS:
        raise ValueError(f"Unknown native component {component!r}.")
    return _native(component) or python_impl


def active() -> dict[str, str]:
    """Implementation (``"python"`` or ``"native"``) used by each component, for result metadata."""
    return {component: "native" if _native(component) else "python" for component in sorted(COMPONENTS)}
