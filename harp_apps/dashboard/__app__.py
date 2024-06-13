"""
Dashboard Application

todo:

remove self ?
remove repetition of configuration namespace ?

"""

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent

from .controllers import DashboardController
from .settings import DashboardSettings

logger = get_logger(__name__)


class DashboardApplication(Application):
    settings_namespace = "dashboard"
    settings_type = DashboardSettings

    @classmethod
    def defaults(cls, settings=None) -> dict:
        settings = settings if settings is not None else {}
        settings.setdefault("port", 4080)
        settings.setdefault("auth", None)
        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.register(DashboardController)
        event.container.add_alias("dashboard.controller", DashboardController)

    async def on_bound(self, event: FactoryBoundEvent):
        # add our controller to the controller resolver
        controller = event.provider.get("dashboard.controller")
        event.resolver.add(self.settings.port, controller)
