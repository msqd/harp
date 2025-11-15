"""
Mixins for application settings.
"""

from pydantic import Field

from .configurables.base import BaseConfigurable


class ApplicationSettingsMixin(BaseConfigurable):
    """
    Mixin that provides an 'enabled' field for application settings.

    This mixin must be used with all application settings types to enable
    per-application enable/disable functionality.
    """

    enabled: bool = Field(default=True, description="Whether the application is enabled")
