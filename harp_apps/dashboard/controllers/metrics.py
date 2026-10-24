from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from harp.http import HttpRequest, HttpResponse

#: Path under which the dashboard port exposes the Prometheus metrics.
METRICS_PATH = "/metrics"


async def metrics_controller() -> HttpResponse:
    """Serves the Prometheus registry in the text exposition format."""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


async def metrics_port_controller(request: HttpRequest) -> HttpResponse:
    """Serves only the metrics on the dedicated, unauthenticated metrics port: nothing else is reachable there."""
    if request.path != METRICS_PATH:
        return HttpResponse("Not found.", status=404, content_type="text/plain")
    return await metrics_controller()
