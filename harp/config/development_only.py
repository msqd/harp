"""
Detection of the settings that are fine on a laptop and unsafe in production.

:func:`development_only_settings` is the single place that knows which settings those are. The server logs them at
startup, and the dashboard reads the same list.
"""

from dataclasses import dataclass

import harp
from harp.typedefs import GlobalSettings


@dataclass(frozen=True)
class DevelopmentOnlySetting:
    #: The setting, as the operator writes it.
    name: str
    #: What is wrong with it and what to use instead.
    message: str


def development_only_settings(config: GlobalSettings) -> list[DevelopmentOnlySetting]:
    """Lists the development-only settings in use, empty when the configuration is production-grade."""
    found = []

    storage = config.get("storage")
    if storage is not None and storage.url.scheme.startswith("sqlite"):
        found.append(
            DevelopmentOnlySetting(
                "storage.url",
                "SQLite storage is meant for development: use PostgreSQL (or MySQL) in production.",
            )
        )

    dashboard = config.get("dashboard")
    if dashboard is not None and getattr(dashboard.auth, "type", None) == "none":
        found.append(
            DevelopmentOnlySetting(
                "dashboard.auth.type",
                "Dashboard authentication is disabled (dashboard.auth.type=none): the dashboard is unauthenticated "
                "and exposes proxied traffic to anyone who can reach its port. Use dashboard.auth.type=basic.",
            )
        )

    if harp.DEBUG:
        found.append(
            DevelopmentOnlySetting(
                "HARP_DEBUG",
                "Debug mode is on and may leak tracebacks in error responses: unset HARP_DEBUG in production.",
            )
        )

    return found
