from .response import ResponseEvent


class ViewEvent(ResponseEvent):
    def __init__(self, request, response, value):
        super().__init__(request, response)
        self._value = value

    @property
    def value(self):
        return self._value
