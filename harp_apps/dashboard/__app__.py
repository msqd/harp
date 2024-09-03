"""
Dashboard Application

"""

from os.path import dirname
from pathlib import Path

from harp import get_logger
from harp.config import Application, OnBindEvent, OnBoundEvent

from .settings import DashboardSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    # Load service definitions, bound to our settings.
    event.container.load(
        Path(dirname(__file__)) / "services.yml",
        bind_settings=event.settings["dashboard"],
    )


async def on_bound(event: OnBoundEvent):
    # This should be feasible using the declarative approach, but for now, we need to ensure the instances are created
    # and alive for them to be registered with the router. The control order is probably wrong, it would be better if
    # the children controllers were injected as a list to the parent controller, but RoutingControllers take the router
    # instance, for now, and register themselves.
    event.provider.set(
        "dashboard.subcontrollers",
        [
            event.provider.get("dashboard.controller.blobs"),
            event.provider.get("dashboard.controller.overview"),
            event.provider.get("dashboard.controller.system"),
            event.provider.get("dashboard.controller.transactions"),
        ],
    )

    # Add our controller to the controller resolver, using the configured dashboard port. This is what will actually
    # make the server to route requests to the dashboard controller when an incoming request is received on the
    # dashboard port.
    event.resolver.add_controller(
        event.provider.get(DashboardSettings).port,
        event.provider.get("dashboard.controller"),
    )


application = Application(
    settings_type=DashboardSettings,
    on_bind=on_bind,
    on_bound=on_bound,
    dependencies=["storage"],
)
