from typing import Optional

from harp.config import Configurable

from .database import DatabaseSettings
from .redis import RedisSettings


class ServicesSettings(Configurable):
    redis: Optional[RedisSettings] = None
    database: Optional[DatabaseSettings] = None
