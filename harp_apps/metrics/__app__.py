from asgi_prometheus import PrometheusMiddleware

from harp import get_logger
from harp.config import Application, OnReadyEvent
from harp.controllers import ProxyControllerResolver

from .decorators import decorate_http_client_send, decorate_proxy_controller
from .settings import MetricsSettings

_metrics_url = "/.prometheus/metrics"

logger = get_logger(__name__)


async def on_ready(event: OnReadyEvent):
    # decorate the asgi app with outer metrics
    event.asgi_app = PrometheusMiddleware(event.asgi_app, metrics_url=_metrics_url, group_paths=["/"])
    event.asgi_app.scopes = ("http",)

    # decorate all controllers with metrics
    resolver = event.provider.get(ProxyControllerResolver)
    for i in resolver:
        resolver[i] = decorate_proxy_controller(
            resolver[i],
            name=resolver.get_controller_name_by_index(i),
            port=resolver.get_controller_port_by_index(i),
        )

    # decorate the http client with metrics
    http_client = event.provider.get("http_client")
    http_client.send = decorate_http_client_send(http_client.send)

    logger.info(f"🌎 Prometheus enabled, metrics under {_metrics_url}.")


application = Application(
    dependencies=["proxy"],
    on_ready=on_ready,
    settings_type=MetricsSettings,
)
