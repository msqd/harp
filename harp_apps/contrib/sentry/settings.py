from typing import Optional

from harp.config import ApplicationSettingsMixin, Configurable, Secret


class SentrySettings(ApplicationSettingsMixin, Configurable):
    dsn: Optional[Secret] = None
