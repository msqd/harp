import os
from functools import lru_cache
from glob import glob
from os.path import dirname

import harp
import harp_apps

EXTENSIONS = [".yml", ".yaml", ".toml"]

# TODO this is clearly not the right place, and it's too static for the future, but let's keep it simple first.
APP_NAMESPACES = ["harp_apps", "harp_contrib"]


@lru_cache
def get_examples_dirname(*, app=None):
    if app is None:
        return os.path.dirname(os.path.abspath(__file__))
    for namespace in APP_NAMESPACES:
        dirname = os.path.join(harp.ROOT_DIR, namespace, app, "examples")
        if os.path.isdir(dirname):
            return dirname
    raise FileNotFoundError(f"Examples directory not found for app {app}.")


def guess_extension(basename):
    if basename.endswith(tuple(EXTENSIONS)):
        return basename
    for ext in EXTENSIONS:
        if os.path.isfile(basename + ext):
            return basename + ext
    raise FileNotFoundError(
        f"Example not found (looked for {basename}.{{{','.join(map(lambda x: x.lstrip('.'), EXTENSIONS))}}})"
    )


def get_example_filename(name):
    if ":" in name:
        app, name = name.split(":", 1)
        return guess_extension(os.path.join(get_examples_dirname(app=app), name))
    return guess_extension(os.path.join(get_examples_dirname(), name))


def get_available_examples_namespaces():
    _default_examples = dirname(__import__("harp.config.examples", fromlist=["__file__"]).__file__)

    _namespaces = {
        None: _default_examples,
    }

    _apps_root_dir = dirname(harp_apps.__file__)

    for _dirname in glob("**/examples", root_dir=_apps_root_dir, recursive=True):
        _pkg, _ = _dirname.rsplit("/", 1)
        _pkg = ".".join(("harp_apps", *_pkg.split("/")))
        _app_pkg = _pkg + ".__app__"
        try:
            __import__(_app_pkg)
        except ImportError:
            continue
        try:
            _example_dirname = dirname(__import__(_pkg + ".examples", fromlist=["__file__"]).__file__)
        except (ImportError, AttributeError):
            continue

        _namespace = _pkg.rsplit(".")[-1]
        if os.path.isdir(_example_dirname):
            _namespaces[_namespace] = _example_dirname
    return _namespaces


@lru_cache
def get_available_examples():
    examples = []
    for _namespace, _dirname in get_available_examples_namespaces().items():
        examples.extend(
            (
                ":".join(filter(None, (_namespace, os.path.splitext(os.path.basename(x))[0])))
                for x in glob(_dirname + "/*.yml")
            )
        )
    return list(sorted(examples))
