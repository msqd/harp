from config.common import ConfigurationBuilder, MapSource
from config.env import EnvVars
from config.yaml import YAMLFile

from harp.settings import ENVIRONMENT


def create_settings(settings=None, *, values=None):
    builder = ConfigurationBuilder()

    # default config
    builder.add_source(MapSource({"dashboard": {}}))
    builder.add_source(YAMLFile("settings.yaml", optional=True))
    builder.add_source(YAMLFile(f"settings.{ENVIRONMENT}.yaml", optional=True))
    if settings:
        builder.add_source(MapSource(settings))

    builder.add_source(EnvVars(prefix="HARP_"))

    if values:
        for k, v in values.items():
            builder.add_value(k, v)

    return builder.build()
