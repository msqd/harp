import traceback

import orjson
from whistle import IAsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_VIEW, ViewEvent


class json(dict):
    """
    This is a marked dict type that our view event listener will recognize and serialize to json in a response.

    Usage::

        def handler():
            return json({"foo": "bar"})

    """

    pass


async def on_json_response(event: ViewEvent):
    if isinstance(event.value, json):
        response = event.response
        response.headers["content-type"] = "application/json"

        try:
            serialized = orjson.dumps(
                event.value,
                option=orjson.OPT_NON_STR_KEYS | orjson.OPT_NAIVE_UTC,
            )
            await response.start(status=200)
            await response.body(serialized)
        except TypeError as exc:
            await response.start(status=500)
            await response.body(
                orjson.dumps(
                    {
                        "error": "Cannot serialize response to json.",
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                        "value": repr(event.value),
                    },
                )
            )

        event.stop_propagation()


def register(dispatcher: IAsyncEventDispatcher):
    dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)
