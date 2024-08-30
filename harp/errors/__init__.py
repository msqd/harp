"""
Errors (:mod:`harp.errors`) module contains the exception hierarchy for Harp.

Contents
--------

"""

__title__ = "Errors"


class BaseError(Exception):
    pass


class ConfigurationError(BaseError):
    pass


class ConfigurationValueError(ConfigurationError, ValueError):
    pass


class ConfigurationRuntimeError(ConfigurationError, RuntimeError):
    pass


class ConfigurationRemovedSettingError(ConfigurationError):
    pass
