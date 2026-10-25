from typing import Any, Optional

from pydantic import Field, IPvAnyNetwork, model_validator

from harp.config import ApplicationSettingsMixin, Configurable
from harp_apps.dashboard.settings.auth import BasicAuthSettings
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

    auth: Optional[BasicAuthSettings] = Field(
        None,
        description="Deprecated. Dashboard users declared in the configuration, signing in with HTTP Basic. They are "
        "imported once as accounts. When not set, the dashboard signs people in with a password, and a setup link "
        "logged at start lets the first administrator in. There is no way to serve the dashboard without "
        "authentication.",
    )

    trusted_proxies: list[IPvAnyNetwork] = Field(
        default_factory=list,
        description="Networks of the reverse proxies in front of the dashboard (`10.0.0.0/8`). Only a connection from "
        "one of them may tell, in `X-Forwarded-For`, which address the client has: the limits on failed sign-ins are "
        "kept per client address, and without this every client behind a proxy shares the address of the proxy.",
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
            if data["auth"].get("type") == "none":
                raise ValueError(
                    "`dashboard.auth.type: none` was removed: the dashboard has no open mode anymore. Remove it, and "
                    "open the setup link HARP logs at start to create the first administrator."
                )
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
