"""
Proxy Application

"""

from .lifecycle import ProxyLifecycle
from .settings import ProxySettings


class ProxyApplication:
    Settings = ProxySettings
    Lifecycle = ProxyLifecycle
