from yaml import dump as yaml_dump
from yaml import load as yaml_load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader


def load(filename):
    with open(filename) as f:
        return yaml_load(f, Loader=Loader)


def dump(source):
    return yaml_dump(source, Dumper=Dumper)
