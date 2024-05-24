import json
from typing import TYPE_CHECKING

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
