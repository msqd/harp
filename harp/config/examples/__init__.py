import os
from functools import lru_cache
from glob import glob

import harp

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


@lru_cache
def get_available_examples():
    return list(sorted((os.path.splitext(os.path.basename(x))[0] for x in glob(get_examples_dirname() + "/*.yml"))))


def _get_available_documentation_examples_filenames():
    return list(sorted((glob(harp.ROOT_DIR + "/docs/**/examples/*.yml", recursive=True))))
