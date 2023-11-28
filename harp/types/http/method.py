import dataclasses
from typing import Union

from harp.types import Maybe


@dataclasses.dataclass(kw_only=True, frozen=True)
class HttpMethod:
    request_body: bool
    response_body: Union[bool, Maybe]
    safe: bool
    idempotent: bool
    cacheable: Union[bool, Maybe]
    allowed_in_forms: bool
    description: str = None
    link: str = None
