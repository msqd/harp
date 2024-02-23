from harp.errors import BaseError


class ConfigurationError(BaseError):
    pass


class ConfigurationValueError(ConfigurationError, ValueError):
    pass


class ConfigurationRuntimeError(ConfigurationError, RuntimeError):
    pass


class ConfigurationRemovedSettingError(ConfigurationError):
    pass
