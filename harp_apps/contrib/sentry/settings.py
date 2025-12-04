from typing import Optional

from harp.config import Configurable, ApplicationSettingsMixin


class SentrySettings(ApplicationSettingsMixin, Configurable):
    dsn: Optional[str] = None
