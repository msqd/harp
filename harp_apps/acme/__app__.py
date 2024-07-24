from harp.config import Application

from .lifecycle import AcmeLifecycle
from .settings import AcmeSettings


class AcmeApplication(Application):
    Settings = AcmeSettings
    Lifecycle = AcmeLifecycle
