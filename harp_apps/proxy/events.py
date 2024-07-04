from typing import Optional

from whistle import Event

from harp.http import HttpResponse
from harp.http.requests import WrappedHttpRequest

EVENT_TRANSACTION_STARTED = "proxy.transaction.started"
EVENT_TRANSACTION_MESSAGE = "proxy.transaction.message"
EVENT_TRANSACTION_ENDED = "proxy.transaction.ended"


class ProxyFilterEvent(Event):
    def __init__(self, endpoint: str, /, *, request: WrappedHttpRequest, response: Optional[HttpResponse] = None):
        self.endpoint = endpoint
        self.request = request
        self.response = response


EVENT_FILTER_REQUEST = "proxy.filter.request"
EVENT_FILTER_RESPONSE = "proxy.filter.response"
