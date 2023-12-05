from json import dumps

from harp.core.asgi.events import ViewEvent


class json(dict):
    pass


async def on_json_response(event: ViewEvent):
    if isinstance(event.value, json):
        responder = event.responder
        await responder.start(status=200, headers={"content-type": "application/json"})
        await responder.body(dumps(event.value))
        event.stop_propagation()
