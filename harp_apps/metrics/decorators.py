import time
from functools import wraps
from typing import Optional

from harp.controllers.typing import IAsyncController
from harp_apps.metrics.constants import (
    CONTROLLER_EXCEPTIONS,
    CONTROLLER_REQUESTS,
    CONTROLLER_REQUESTS_IN_PROGRESS,
    CONTROLLER_REQUESTS_TIME,
    CONTROLLER_RESPONSES,
    REMOTE_EXCEPTIONS,
    REMOTE_REQUESTS,
    REMOTE_REQUESTS_IN_PROGRESS,
    REMOTE_REQUESTS_TIME,
    REMOTE_RESPONSES,
)


def _instrument(wrapped, *, requests, in_progress, responses, exceptions, duration, get_labels, status_attribute):
    """
    Wraps an async callable taking a request as first argument, collecting the given prometheus metrics.
    """

    @wraps(wrapped)
    async def wrapper(request, *args, **kwargs):
        labels = get_labels(request)
        requests.labels(**labels).inc()
        in_progress.labels(**labels).inc()

        before_time = time.perf_counter()
        try:
            response = await wrapped(request, *args, **kwargs)
            responses.labels(**labels, status=getattr(response, status_attribute, "-")).inc()
            return response
        except Exception as exc:  # noqa: BLE001
            exceptions.labels(**labels, exception=type(exc).__name__).inc()
            raise
        finally:
            after_time = time.perf_counter()
            duration.labels(**labels).observe(after_time - before_time)
            in_progress.labels(**labels).dec()

    return wrapper


def decorate_proxy_controller(wrapped: IAsyncController, *, name: Optional[str] = None, port: Optional[int] = None):
    """
    Decorates a builtin or custom proxy controller to collect metrics for prometheus.
    """
    common_labels = dict(name=(name or "-"), port=(port or "-"))

    return _instrument(
        wrapped,
        requests=CONTROLLER_REQUESTS,
        in_progress=CONTROLLER_REQUESTS_IN_PROGRESS,
        responses=CONTROLLER_RESPONSES,
        exceptions=CONTROLLER_EXCEPTIONS,
        duration=CONTROLLER_REQUESTS_TIME,
        get_labels=lambda request: {**common_labels, "method": request.method},
        status_attribute="status",
    )


def decorate_http_client_send(wrapped):
    """
    Decorates the httpx async client send method to collect metrics for prometheus.
    """
    return _instrument(
        wrapped,
        requests=REMOTE_REQUESTS,
        in_progress=REMOTE_REQUESTS_IN_PROGRESS,
        responses=REMOTE_RESPONSES,
        exceptions=REMOTE_EXCEPTIONS,
        duration=REMOTE_REQUESTS_TIME,
        get_labels=lambda request: {
            "name": request.extensions.get("harp", {}).get("endpoint", "-"),
            "method": request.method,
        },
        status_attribute="status_code",
    )
