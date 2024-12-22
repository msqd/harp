from typing import Optional

from pydantic import Field

from harp.config import Configurable


class DevserverSettings(Configurable):
    enabled: bool = Field(
        True,
        description="Enable or disable the development server.",
    )
    port: Optional[int] = Field(
        None,
        description=(
            "Port on which the development server will be served (internal). The proxy will forward dashboard "
            "requests to this port, if enabled."
        ),
    )
