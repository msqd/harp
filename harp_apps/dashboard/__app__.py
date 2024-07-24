"""
Dashboard Application

todo:

remove self ?
remove repetition of configuration namespace ?

"""

from harp import get_logger
from harp.config import Application, FactoryBindEvent, FactoryBoundEvent

from .controllers import DashboardController
from .settings import DashboardSettings

logger = get_logger(__name__)


class DashboardApplication(Application):
    depends_on = {"storage"}
    Settings = DashboardSettings

    class Lifecycle:
        @staticmethod
        async def on_bind(event: FactoryBindEvent):
            event.container.register(DashboardController)
            event.container.add_alias("dashboard.controller", DashboardController)

        @staticmethod
        async def on_bound(event: FactoryBoundEvent):
            # add our controller to the controller resolver
            controller = event.provider.get("dashboard.controller")
            settings = event.provider.get(DashboardSettings)
            event.resolver.add(settings.port, controller)
