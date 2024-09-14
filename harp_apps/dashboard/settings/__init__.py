from typing import Optional

from pydantic import Field

from harp.config import Configurable
from harp_apps.dashboard.settings.auth import BasicAuthSettings
from harp_apps.dashboard.settings.devserver import DevserverSettings


class DashboardSettings(Configurable):
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

    enable_ui: bool = Field(
        True,
        description="DEPRECATED – Whether to enable the dashboard UI.",
    )

    public_url: Optional[str] = Field(
        None,
        description="Public URL of the dashboard application, used to generate absolute links, for example in notifications.",
    )
