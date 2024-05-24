import dataclasses
from typing import Union

from harp.typing import Maybe


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


HTTP_METHODS = {
    "GET": HttpMethod(
        request_body=False,
        response_body=True,
        safe=True,
        idempotent=True,
        cacheable=True,
        allowed_in_forms=True,
        description=(
            "The GET method requests a representation of the specified resource. Requests using GET should only "
            "retrieve data."
        ),
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET",
    ),
    "HEAD": HttpMethod(
        request_body=False,
        response_body=False,
        safe=True,
        idempotent=True,
        cacheable=True,
        allowed_in_forms=False,
        description="The HEAD method asks for a response identical to a GET request, but without the response body.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/HEAD",
    ),
    "POST": HttpMethod(
        request_body=True,
        response_body=True,
        safe=False,
        idempotent=False,
        cacheable=Maybe,
        allowed_in_forms=True,
        description=(
            "The POST method submits an entity to the specified resource, often causing a change in state or side "
            "effects on the server."
        ),
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST",
    ),
    "PUT": HttpMethod(
        request_body=True,
        response_body=Maybe,
        safe=False,
        idempotent=True,
        cacheable=False,
        allowed_in_forms=False,
        description=(
            "The PUT method replaces all current representations of the target resource with the request payload."
        ),
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT",
    ),
    "DELETE": HttpMethod(
        request_body=False,
        response_body=Maybe,
        safe=False,
        idempotent=True,
        cacheable=False,
        allowed_in_forms=False,
        description="The DELETE method deletes the specified resource.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/DELETE",
    ),
    "CONNECT": HttpMethod(
        request_body=False,
        response_body=False,
        safe=False,
        idempotent=False,
        cacheable=False,
        allowed_in_forms=False,
        description="The CONNECT method establishes a tunnel to the server identified by the target resource.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/CONNECT",
    ),
    "OPTIONS": HttpMethod(
        request_body=False,
        response_body=True,
        safe=True,
        idempotent=True,
        cacheable=False,
        allowed_in_forms=False,
        description="The OPTIONS method describes the communication options for the target resource.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/OPTIONS",
    ),
    "TRACE": HttpMethod(
        request_body=False,
        response_body=False,
        safe=True,
        idempotent=True,
        cacheable=False,
        allowed_in_forms=False,
        description="The TRACE method performs a message loop-back test along the path to the target resource.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/TRACE",
    ),
    "PATCH": HttpMethod(
        request_body=True,
        response_body=Maybe,
        safe=False,
        idempotent=False,
        cacheable=Maybe,
        allowed_in_forms=False,
        description="The PATCH method applies partial modifications to a resource.",
        link="https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH",
    ),
}
