import importlib.util

try:
    import rich_click as click
except ImportError:
    import click


def assert_package_is_available(package_name: str):
    if importlib.util.find_spec(package_name) is None:
        raise ModuleNotFoundError(f"Package {package_name!r} is not available.")


def check_packages(*pkgs):
    for pkg in pkgs:
        try:
            assert_package_is_available(pkg)
        except ModuleNotFoundError:
            return False
    return True


__all__ = [
    "assert_package_is_available",
    "check_packages",
    "click",
]
