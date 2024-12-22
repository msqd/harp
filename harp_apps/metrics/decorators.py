import time
from functools import wraps
from typing import Optional

import httpx

from harp.controllers.typing import IAsyncController
from harp.http import HttpRequest, HttpResponse
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


def decorate_proxy_controller(wrapped: IAsyncController, *, name: Optional[str] = None, port: Optional[int] = None):
    """
    Decorates a builtin or custom proxy controller to collect metrics for prometheus.
    """
    common_labels = dict(name=(name or "-"), port=(port or "-"))

    @wraps(wrapped)
    async def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        labels = {**common_labels, "method": request.method}
        CONTROLLER_REQUESTS.labels(**labels).inc()
        CONTROLLER_REQUESTS_IN_PROGRESS.labels(**labels).inc()

        before_time = time.perf_counter()
        try:
            response = await wrapped(request, *args, **kwargs)
            CONTROLLER_RESPONSES.labels(**labels, status=getattr(response, "status", "-")).inc()
            return response
        except Exception as exc:  # noqa: BLE001
            CONTROLLER_EXCEPTIONS.labels(**labels, path=request.path, exception=type(exc).__name__).inc()
            raise exc from None
        finally:
            after_time = time.perf_counter()
            CONTROLLER_REQUESTS_TIME.labels(**labels).observe(after_time - before_time)
            CONTROLLER_REQUESTS_IN_PROGRESS.labels(**labels).dec()

    return wrapper


def decorate_http_client_send(wrapped):
    """
    Decorates the httpx async client send method to collect metrics for prometheus.
    """

    @wraps(wrapped)
    async def wrapper(request: httpx.Request, *args, **kwargs) -> httpx.Response:
        labels = {"name": request.extensions.get("harp", {}).get("endpoint", "-"), "method": request.method}
        REMOTE_REQUESTS.labels(**labels).inc()
        REMOTE_REQUESTS_IN_PROGRESS.labels(**labels).inc()

        before_time = time.perf_counter()
        try:
            response = await wrapped(request, *args, **kwargs)
            REMOTE_RESPONSES.labels(**labels, status=getattr(response, "status_code", "-")).inc()
            return response
        except Exception as exc:  # noqa: BLE001
            REMOTE_EXCEPTIONS.labels(**labels, url=str(request.url), exception=type(exc).__name__).inc()
            raise exc from None
        finally:
            after_time = time.perf_counter()
            REMOTE_REQUESTS_TIME.labels(**labels).observe(after_time - before_time)
            REMOTE_REQUESTS_IN_PROGRESS.labels(**labels).dec()

    return wrapper
