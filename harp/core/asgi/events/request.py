from functools import cached_property

from harp.core.event_dispatcher import BaseEvent


class RequestEvent(BaseEvent):
    def __init__(self, request):
        self._request = request
        self._controller = None

    @cached_property
    def request(self):
        return self._request

    @property
    def controller(self):
        return self._controller

    def set_controller(self, controller):
        self._controller = controller
