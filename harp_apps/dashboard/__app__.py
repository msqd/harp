"""
Dashboard Application

"""

from os.path import dirname
from pathlib import Path

from harp import get_logger
from harp.config import Application, OnBindEvent, OnBoundEvent
from harp_apps.auth.settings import AuthSettings

from .controllers.metrics import metrics_port_controller
from .settings import DashboardSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    # Load service definitions, bound to our settings.
    event.container.load(
        Path(dirname(__file__)) / "services.yml",
        bind_settings=event.settings["dashboard"],
    )


def _base_url(settings: DashboardSettings) -> str:
    if settings.public_url:
        return settings.public_url
    host = "localhost" if settings.host in ("[::]", "::", "0.0.0.0", "") else settings.host
    return f"http://{host}:{settings.port}"


async def _publish_setup_link(event: OnBoundEvent, settings: DashboardSettings):
    """While no Admin exists, the logs hold the link that lets the first one in. The users of a Basic configuration
    become Admins when they are imported, so they need none."""
    if settings.auth and settings.auth.users:
        return
    link = await event.provider.get("auth.setup").publish(_base_url(settings))
    if link:
        logger.warning(
            "There is no administrator yet: nobody can sign in to the dashboard until you open this link, which creates "
            f"the first one (single use, valid for {event.provider.get(AuthSettings).setup_link_hours} hours, and "
            f"replaced at each start): {link}"
        )


async def on_bound(event: OnBoundEvent):
    # This should be feasible using the declarative approach, but for now, we need to ensure the instances are created
    # and alive for them to be registered with the router. The control order is probably wrong, it would be better if
    # the children controllers were injected as a list to the parent controller, but RoutingControllers take the router
    # instance, for now, and register themselves.
    event.provider.set(
        "dashboard.subcontrollers",
        [
            event.provider.get("dashboard.controller.auth"),
            event.provider.get("dashboard.controller.blobs"),
            event.provider.get("dashboard.controller.overview"),
            event.provider.get("dashboard.controller.system"),
            event.provider.get("dashboard.controller.transactions"),
        ],
    )

    # Add our controller to the controller resolver, using the configured dashboard port. This is what will actually
    # make the server to route requests to the dashboard controller when an incoming request is received on the
    # dashboard port.
    settings = event.provider.get(DashboardSettings)
    await _publish_setup_link(event, settings)
    event.resolver.add_controller(
        event.provider.get("dashboard.controller"),
        name="dashboard",
        port=settings.port,
        host=settings.host,
    )

    metrics_port = settings.metrics_port
    if metrics_port:
        event.resolver.add_controller(metrics_port_controller, name="metrics", port=metrics_port)


application = Application(
    dependencies=["storage", "auth"],
    settings_type=DashboardSettings,
    on_bind=on_bind,
    on_bound=on_bound,
)
