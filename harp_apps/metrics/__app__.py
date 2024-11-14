import time
from functools import wraps
from typing import Optional

from asgi_prometheus import PrometheusMiddleware
from prometheus_client import Counter, Gauge, Histogram

from harp import get_logger
from harp.config import Application, OnReadyEvent
from harp.controllers import ProxyControllerResolver
from harp.controllers.typing import IAsyncController
from harp.http import HttpRequest, HttpResponse

from .settings import MetricsSettings

_metrics_url = "/.prometheus/metrics"

logger = get_logger(__name__)

CONTROLLER_REQUESTS = Counter(
    "controller_requests_count",
    "Count of controller requests by route name, port and method.",
    ["name", "port", "method"],
)

CONTROLLER_REQUESTS_TIME = Histogram(
    "controller_requests_time",
    "Histogram of controller requests processing time by route name, port and method (in seconds)",
    ["name", "port", "method"],
)

CONTROLLER_REQUESTS_IN_PROGRESS = Gauge(
    "controller_requests_in_progress",
    "Gauge of controller requests by route name, port and method currently being processed",
    ["name", "port", "method"],
)

CONTROLLER_RESPONSES = Counter(
    "controller_responses_count",
    "Count of controller responses by route name, port, method and status and status codes.",
    ["name", "port", "method", "status"],
)

CONTROLLER_EXCEPTIONS = Counter(
    "controller_exceptions_count",
    "Count of exceptions raised in controllers by route name, port, method, path and exception type",
    ["name", "port", "method", "path", "exception"],
)


def decorate_controller(controller: IAsyncController, *, name: Optional[str] = None, port: Optional[int] = None):
    name, port = (name or "-"), (port or "-")

    @wraps(controller)
    async def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        CONTROLLER_REQUESTS.labels(
            name=name,
            port=port,
            method=request.method,
        ).inc()

        CONTROLLER_REQUESTS_IN_PROGRESS.labels(
            name=name,
            port=port,
            method=request.method,
        ).inc()

        try:
            before_time = time.perf_counter()
            response = await controller(request, *args, **kwargs)
            after_time = time.perf_counter()
            CONTROLLER_REQUESTS_TIME.labels(
                name=name,
                port=port,
                method=request.method,
            ).observe(after_time - before_time)
            CONTROLLER_RESPONSES.labels(
                name=name,
                port=port,
                method=request.method,
                status=getattr(response, "status", "-"),
            ).inc()
        except Exception as exc:  # noqa: BLE001
            CONTROLLER_EXCEPTIONS.labels(
                name=name,
                port=port,
                method=request.method,
                path=request.path,
                exception=type(exc).__name__,
            ).inc()
            raise exc from None
        else:
            return response
        finally:
            CONTROLLER_REQUESTS_IN_PROGRESS.labels(
                name=name,
                port=port,
                method=request.method,
            ).dec()

    return wrapped


async def on_ready(event: OnReadyEvent):
    event.asgi_app = PrometheusMiddleware(event.asgi_app, metrics_url=_metrics_url, group_paths=["/"])
    event.asgi_app.scopes = ("http",)

    resolver = event.provider.get(ProxyControllerResolver)
    for i in resolver:
        resolver[i] = decorate_controller(
            resolver[i],
            name=resolver.get_controller_name_by_index(i),
            port=resolver.get_controller_port_by_index(i),
        )

    logger.info(f"🌎 PrometheusMiddleware enabled, metrics under {_metrics_url}.")


application = Application(
    dependencies=["proxy"],
    on_ready=on_ready,
    settings_type=MetricsSettings,
)
