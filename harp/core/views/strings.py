from harp.core.asgi.events.view import ViewEvent


class html(str):
    content_type = "text/html"


async def on_string_response(event: ViewEvent):
    if isinstance(event.value, str):
        response = event.response
        await response.start(status=200, headers={"content-type": getattr(event.value, "content_type", "text/plain")})
        await response.body(event.value)
        event.stop_propagation()
