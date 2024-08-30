from typing import Optional

from harp.config import Configurable


class DevserverSettings(Configurable):
    enabled: bool = True
    port: Optional[int] = None
