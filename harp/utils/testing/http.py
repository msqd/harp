import http

import pytest

from harp.typing import Maybe, NotSet


def parametrize_with_http_status_codes(include=None):
    statuses = list(map(lambda x: x.value, http.HTTPStatus))
    if include is not None:
        statuses = list(filter(lambda x: x // 100 in include, statuses))
    return pytest.mark.parametrize("status_code", statuses)


def parametrize_with_http_methods(
    *,
    include_safe=NotSet,
    include_unsafe=NotSet,
    include_idempotent=NotSet,
    include_non_idempotent=NotSet,
    include_standard=NotSet,
    include_non_standard=NotSet,
    include_having_request_body=NotSet,
    include_maybe_having_request_body=NotSet,
    include_not_having_request_body=NotSet,
    include_having_response_body=NotSet,
    include_maybe_having_response_body=NotSet,
    include_not_having_response_body=NotSet,
    exclude=(),
):
    from harp.http.utils import HTTP_METHODS

    if {
        include_safe,
        include_unsafe,
        include_idempotent,
        include_non_idempotent,
        include_standard,
        include_non_standard,
        include_having_request_body,
        include_maybe_having_request_body,
        include_not_having_request_body,
        include_having_response_body,
        include_maybe_having_response_body,
        include_not_having_response_body,
    } == {NotSet}:
        include_standard = True

    methods = set()
    if include_safe is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.safe is True}
    if include_unsafe is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.safe is False}
    if include_idempotent is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.idempotent is True}
    if include_non_idempotent is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.idempotent is False}
    if include_standard is True:
        methods |= set(HTTP_METHODS.keys())
    if include_non_standard is True:
        methods |= {"BREW", "REMIX"}
    if include_having_request_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.request_body is True}
    if include_not_having_request_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.request_body is False}
    if include_maybe_having_request_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.request_body is Maybe}
    if include_having_response_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.response_body is True}
    if include_not_having_response_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.response_body is False}
    if include_maybe_having_response_body is True:
        methods |= {name for name, method in HTTP_METHODS.items() if method.response_body is Maybe}

    if include_safe is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.safe is True}
    if include_unsafe is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.safe is False}
    if include_idempotent is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.idempotent is True}
    if include_non_idempotent is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.idempotent is False}
    if include_standard is False:
        methods -= set(HTTP_METHODS.keys())
    if include_non_standard is False:
        methods -= {"BREW", "REMIX"}
    if include_having_request_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.request_body is True}
    if include_not_having_request_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.request_body is False}
    if include_maybe_having_request_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.request_body is Maybe}
    if include_having_response_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.response_body is True}
    if include_not_having_response_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.response_body is False}
    if include_maybe_having_response_body is False:
        methods -= {name for name, method in HTTP_METHODS.items() if method.response_body is Maybe}

    methods -= set(exclude)

    return pytest.mark.parametrize("method", list(sorted(methods)))
