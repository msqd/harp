from typing import Literal

from pydantic import BaseModel


class SystemPutProxyInput(BaseModel):
    endpoint: str
    action: Literal["up", "down", "checking"]
    url: str
