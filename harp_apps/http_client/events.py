from typing import Optional

from httpx import Request, Response
from whistle import Event


class HttpClientFilterEvent(Event):
    def __init__(self, request: Request, response: Optional[Response] = None):
        self.request = request
        self.response = response


EVENT_FILTER_HTTP_CLIENT_REQUEST = "http_client.filter.request"
EVENT_FILTER_HTTP_CLIENT_RESPONSE = "http_client.filter.response"
