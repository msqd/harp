import traceback
from decimal import Decimal

import orjson
from whistle import IAsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_VIEW, ViewEvent
from harp.http import HttpResponse

STRINGIFIABLES = (Decimal,)

try:
    from freezegun.api import FakeDatetime

    STRINGIFIABLES += (FakeDatetime,)
except ImportError:
    pass

LISTIFIABLES = (set,)


def default(obj):
    if isinstance(obj, STRINGIFIABLES):
        return str(obj)
    if isinstance(obj, LISTIFIABLES):
        return list(sorted(obj))
    raise TypeError


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
        content_type = "application/json"
        try:
            serialized = orjson.dumps(
                event.value,
                option=orjson.OPT_NON_STR_KEYS | orjson.OPT_NAIVE_UTC,
                default=default,
            )
            event.set_response(
                HttpResponse(serialized, status=200, content_type=content_type),
            )
        except TypeError as exc:
            event.set_response(
                HttpResponse(
                    orjson.dumps(
                        {
                            "error": "Cannot serialize response to json.",
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "traceback": traceback.format_exc(),
                            "value": repr(event.value),
                        },
                    ),
                    status=500,
                    content_type=content_type,
                ),
            )


def register(dispatcher: IAsyncEventDispatcher):
    dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)
