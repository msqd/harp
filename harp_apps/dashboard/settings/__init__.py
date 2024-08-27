from typing import Optional, Union

from pydantic import Field

from harp.config import Configurable
from harp_apps.dashboard.settings.auth import BasicAuthSettings
from harp_apps.dashboard.settings.devserver import DevserverSettings


class DashboardSettings(Configurable):
    """Root settings for the dashboard application."""

    port: int = 4080
    auth: Union[BasicAuthSettings] = Field(None, discriminator="type")
    devserver: Optional[DevserverSettings] = DevserverSettings()
    public_url: Optional[str] = None
