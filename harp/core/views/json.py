from json import dumps

from harp.core.asgi.events import ViewEvent


class json(dict):
    pass


async def on_json_response(event: ViewEvent):
    if isinstance(event.value, json):
        response = event.response
        await response.start(status=200, headers={"content-type": "application/json"})
        await response.body(dumps(event.value))
        event.stop_propagation()
