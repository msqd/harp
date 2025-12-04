from typing import Any, Optional

from pydantic import Field, model_validator

from harp.config import ApplicationSettingsMixin, Configurable
from harp_apps.dashboard.settings.auth import BasicAuthSettings
from harp_apps.dashboard.settings.devserver import DevserverSettings


class DashboardSettings(ApplicationSettingsMixin, Configurable):
    """Root settings for the dashboard application."""

    port: int = Field(
        4080,
        description="Port on which the dashboard application will be served.",
    )

    auth: Optional[BasicAuthSettings] = Field(
        None,
        discriminator="type",
        description="Authentication settings for the dashboard.",
    )

    devserver: Optional[DevserverSettings] = Field(
        default_factory=DevserverSettings,
        description="Development server settings, only useful for internal frontend development.",
    )

    public_url: Optional[str] = Field(
        None,
        description="Public URL of the dashboard application, used to generate absolute links, for example in notifications.",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_deprecated_enable_ui(cls, data: Any) -> Any:
        if isinstance(data, dict) and "enable_ui" in data:
            raise ValueError(
                "The 'enable_ui' setting has been removed. "
                "Use 'enabled: false' instead to disable the dashboard application entirely."
            )
        return data
