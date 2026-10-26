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
                "SQLite storage is meant for development: use PostgreSQL in production.",
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
