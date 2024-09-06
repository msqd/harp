from typing import Optional

from harp.config import Configurable


class SentrySettings(Configurable):
    dsn: Optional[str] = None
