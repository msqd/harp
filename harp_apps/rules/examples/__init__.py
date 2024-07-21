import os

from harp.utils.config import yaml


def load(name):
    return yaml.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))


def dump(source):
    return yaml.dump(source)
