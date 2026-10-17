import traceback
from functools import cached_property
from typing import Optional

import harp
from multidict import MultiDict, MultiDictProxy

from .typing import BaseHttpMessage


class RejectedRequest(Exception):
    """Raised while reading a request that must be answered with an error status and not be processed further."""

    def __init__(self, message: str, /, *, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class ClientDisconnected(Exception):
    """Raised while reading a request body when the client went away before sending all of it."""


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
            if harp.DEBUG:
                out += "\n\n" + "".join(traceback.format_exception(self.exception))
            return out.encode()
        return self.message.encode()
