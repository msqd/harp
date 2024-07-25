"""
Dashboard Application

todo:

remove self ?
remove repetition of configuration namespace ?

"""

from harp import get_logger
from harp.config import Application, OnBindEvent, OnBoundEvent

from .controllers import DashboardController
from .settings import DashboardSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    event.container.register(DashboardController)
    event.container.add_alias("dashboard.controller", DashboardController)


async def on_bound(event: OnBoundEvent):
    # add our controller to the controller resolver
    controller = event.provider.get("dashboard.controller")
    settings = event.provider.get(DashboardSettings)
    event.resolver.add(settings.port, controller)


application = Application(
    settings_type=DashboardSettings,
    on_bind=on_bind,
    on_bound=on_bound,
    dependencies=["storage"],
)
