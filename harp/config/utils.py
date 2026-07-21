import os

from harp.utils.packages import import_string


def get_configuration_builder_type():
    edition = os.environ.get("HARP_EDITION", "harp_apps")
    try:
        ConfigurationBuilder = import_string(f"{edition}.ConfigurationBuilder")
    except (ImportError, AttributeError):
        from harp.config import ConfigurationBuilder
    return ConfigurationBuilder
