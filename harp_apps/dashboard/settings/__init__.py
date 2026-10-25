from typing import Any, Optional, Union

from pydantic import Field, model_validator

from harp.config import ApplicationSettingsMixin, Configurable
from harp_apps.dashboard.settings.auth import BasicAuthSettings, NoAuthSettings
from harp_apps.dashboard.settings.devserver import DevserverSettings


class DashboardSettings(ApplicationSettingsMixin, Configurable):
    """Root settings for the dashboard application."""

    host: str = Field(
        "[::]",
        description="Address on which the dashboard application will listen. The default listens on every interface, "
        "which a published Docker port needs. Use `127.0.0.1` to listen on the loopback interface only.",
    )

    port: int = Field(
        4080,
        description="Port on which the dashboard application will be served.",
    )

    metrics_port: Optional[int] = Field(
        None,
        description="Port on which the Prometheus metrics (`/metrics`) are also served, unauthenticated. Disabled by "
        "default. Metrics are always served on the dashboard port, under the dashboard authentication.",
    )

    auth: Optional[Union[BasicAuthSettings, NoAuthSettings]] = Field(
        None,
        discriminator="type",
        description="Authentication settings for the dashboard. When not set, the dashboard requires a login with the "
        "`admin` user and a random password generated and logged at each boot. Use `type: none` to explicitly serve "
        "the dashboard without authentication.",
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
    def default_auth_type_to_basic(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("auth"), dict):
            return {**data, "auth": {"type": "basic", **data["auth"]}}
        return data

    @model_validator(mode="before")
    @classmethod
    def reject_deprecated_enable_ui(cls, data: Any) -> Any:
        if isinstance(data, dict) and "enable_ui" in data:
            raise ValueError(
                "The 'enable_ui' setting has been removed. "
                "Use 'enabled: false' instead to disable the dashboard application entirely."
            )
        return data
