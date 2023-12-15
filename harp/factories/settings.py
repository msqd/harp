import os

from config.common import ConfigurationBuilder, MapSource
from config.env import EnvVars
from config.ini import INIFile
from config.json import JSONFile
from config.toml import TOMLFile
from config.yaml import YAMLFile


def create_settings(settings=None, *, values=None, files=None):
    builder = ConfigurationBuilder()

    # default config
    builder.add_source(MapSource({"dashboard": {}}))
    builder.add_source(YAMLFile("/etc/harp.yaml", optional=True))
    if files:
        for file in files:
            _, ext = os.path.splitext(file)
            if ext in (".yaml", ".yml"):
                builder.add_source(YAMLFile(file))
            elif ext in (".json",):
                builder.add_source(JSONFile(file))
            elif ext in (".ini",):
                builder.add_source(INIFile(file))
            elif ext in (".toml",):
                builder.add_source(TOMLFile(file))
            else:
                raise ValueError(f"Unknown file extension: {ext}")
    if settings:
        builder.add_source(MapSource(settings))

    builder.add_source(EnvVars(prefix="HARP_"))

    if values:
        for k, v in values.items():
            builder.add_value(k, v)

    return builder.build()
