from harp.asgi.events import ControllerViewEvent
from harp.http import HttpResponse


class html(str):
    content_type = "text/html"


async def on_string_response(event: ControllerViewEvent):
    if isinstance(event.value, str):
        content_type = getattr(event.value, "content_type", "text/plain")
        event.set_response(
            HttpResponse(event.value, content_type=content_type),
        )
