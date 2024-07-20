import os

import yaml
from yaml import dump as yaml_dump
from yaml import load as yaml_load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader


def multiline_str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, multiline_str_presenter, Dumper=yaml.Dumper)


def load(name):
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    with open(filename) as f:
        return yaml_load(f, Loader=Loader)


def dump(source):
    return yaml_dump(source, Dumper=Dumper)
