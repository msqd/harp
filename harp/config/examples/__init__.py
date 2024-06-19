import os
from functools import lru_cache
from glob import glob


@lru_cache
def get_examples_dirname():
    return os.path.dirname(os.path.abspath(__file__))


def get_example_filename(name):
    return os.path.join(get_examples_dirname(), f"{name}.yml")


@lru_cache
def get_available_examples():
    return list(sorted((os.path.splitext(os.path.basename(x))[0] for x in glob(get_examples_dirname() + "/*.yml"))))
