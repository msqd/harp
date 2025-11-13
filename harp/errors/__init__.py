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


class MissingDependencyError(ConfigurationError):
    """Raised when an application declares a dependency that is not enabled."""

    pass


class CircularDependencyError(ConfigurationError):
    """Raised when circular dependencies are detected between applications."""

    pass
