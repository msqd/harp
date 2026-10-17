from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from harp.http import HttpResponse

#: Path under which the dashboard port exposes the Prometheus metrics.
METRICS_PATH = "/metrics"


async def metrics_controller() -> HttpResponse:
    """Serves the Prometheus registry in the text exposition format."""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
