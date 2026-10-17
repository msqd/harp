"""
Choice between pure Python and native implementations, driven by the ``HARP_NATIVE`` environment variable.

- unset or ``none``: pure Python everywhere (the reference).
- ``all``: native wherever the extension provides a component, hard failure if the extension is missing.
- ``a,b``: native for the listed components, hard failure if the extension or a listed implementation is missing.

The extension is expected at ``harp._native._core``, exposing each component under its name.

"""

import os
from importlib import import_module
from typing import Callable

#: Components that may have a native implementation.
COMPONENTS: frozenset[str] = frozenset()


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


def _core():
    try:
        return import_module("harp._native._core")
    except ImportError as exc:
        raise NativeUnavailableError("HARP_NATIVE requests native code but harp._native._core is missing.") from exc


def _native(component: str) -> Callable | None:
    requested, strict = _requested()
    if component not in requested:
        return None
    impl = getattr(_core(), component, None)
    if impl is None and strict:
        raise NativeUnavailableError(f"HARP_NATIVE requests native {component!r} but harp._native._core has none.")
    return impl


def select(component: str, python_impl: Callable) -> Callable:
    """Return the implementation of ``component`` to use, according to ``HARP_NATIVE``."""
    if component not in COMPONENTS:
        raise ValueError(f"Unknown native component {component!r}.")
    return _native(component) or python_impl


def active() -> dict[str, str]:
    """Implementation (``"python"`` or ``"native"``) used by each component, for result metadata."""
    return {component: "native" if _native(component) else "python" for component in sorted(COMPONENTS)}
