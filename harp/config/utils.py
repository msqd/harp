import os


def get_configuration_builder_type():
    edition = os.environ.get("HARP_EDITION", "harp_apps")
    try:
        ConfigurationBuilder = __import__(edition, fromlist=["ConfigurationBuilder"]).ConfigurationBuilder
    except (ImportError, AttributeError):
        from harp.config import ConfigurationBuilder
    return ConfigurationBuilder
