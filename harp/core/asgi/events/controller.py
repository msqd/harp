from .request import RequestEvent


class ControllerEvent(RequestEvent):
    def __init__(self, request, controller):
        super().__init__(request)
        self._controller = controller
