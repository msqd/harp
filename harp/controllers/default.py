import json
from typing import TYPE_CHECKING

from harp.asgi.events import RequestEvent
from harp.http import HttpResponse
from harp.utils.json import BytesEncoder

if TYPE_CHECKING:
    from harp.http import HttpRequest


async def dump_request_controller(request: "HttpRequest"):
    """
    TODO: use orjson ?
    """
    try:
        scope = request._impl.asgi_scope
    except AttributeError:
        scope = {}

    return HttpResponse(json.dumps(scope, cls=BytesEncoder), content_type="application/json")


async def not_found_controller():
    return HttpResponse("Not found.", status=404, content_type="text/plain")


async def ok_controller():
    return HttpResponse("Ok.", status=200)


async def on_health_request(event: RequestEvent):
    if event.request.path == "/healthz":
        event.set_controller(ok_controller)
        event.stop_propagation()
