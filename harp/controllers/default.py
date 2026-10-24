from harp.asgi.events import RequestEvent
from harp.http import HttpResponse


async def not_found_controller():
    return HttpResponse("Not found.", status=404, content_type="text/plain")


async def ok_controller():
    return HttpResponse("Ok.", status=200)


async def on_health_request(event: RequestEvent):
    if event.request.path == "/healthz":
        event.set_controller(ok_controller)
        event.stop_propagation()
