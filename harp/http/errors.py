from functools import cached_property
from typing import Optional

from multidict import MultiDict, MultiDictProxy

from .typing import BaseHttpMessage


class HttpError(BaseHttpMessage):
    kind = "error"

    def __init__(
        self,
        message: str,
        /,
        *,
        exception: Optional[Exception] = None,
        status=500,
        verbose_message=None,
    ):
        super().__init__()
        self.message = message
        self.exception = exception
        self.status = status
        self.verbose_message = verbose_message or message

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
