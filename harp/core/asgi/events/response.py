from .request import RequestEvent


class ResponseEvent(RequestEvent):
    def __init__(self, request, response):
        super().__init__(request)
        self.response = response
