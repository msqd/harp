from functools import cached_property

from multidict import MultiDict, MultiDictProxy

from .typing import BaseHttpMessage


class HttpError(BaseHttpMessage):
    kind = "error"

    def __init__(self, message: str, /, *, exception: Exception = None):
        super().__init__()
        self.message = message
        self.exception = exception

    @cached_property
    def headers(self) -> MultiDictProxy:
        return MultiDictProxy(MultiDict())

    @cached_property
    def body(self) -> bytes:
        if self.exception:
            msg = str(self.exception)
            out = type(self.exception).__name__
            if msg:
                out += f": {msg}"
            return out.encode()
        return self.message.encode()
