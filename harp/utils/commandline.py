import builtins
import importlib.util

code = None

if getattr(builtins, "__sphinx__", False):

    def code(x):
        return ":code:`" + x + "`"


try:
    import rich_click as click

    click.rich_click.USE_RICH_MARKUP = True

    if not code:

        def code(x):
            return "[code]" + x + "[/]"

except ImportError:
    import click

if not code:

    def code(x):
        return x


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
