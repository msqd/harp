import http

import pytest

from harp.http.utils import HTTP_METHODS
from harp.typing import Maybe, NotSet


def parametrize_with_http_status_codes(include=None):
    statuses = [status.value for status in http.HTTPStatus]
    if include is not None:
        statuses = [status for status in statuses if status // 100 in include]
    return pytest.mark.parametrize("status_code", statuses)


def _filter_methods_by_attribute(attribute, value):
    return {name for name, method in HTTP_METHODS.items() if getattr(method, attribute) is value}


def _update_methods_set(methods, include, attribute, value):
    if include is True:
        methods |= _filter_methods_by_attribute(attribute, value)
    elif include is False:
        methods -= _filter_methods_by_attribute(attribute, value)


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
    """
    Parametrize a test with HTTP methods based on various inclusion and exclusion criteria.

    Parameters:
    - include_safe (bool or NotSet): Include safe methods (e.g., GET, HEAD).
    - include_unsafe (bool or NotSet): Include unsafe methods (e.g., POST, PUT).
    - include_idempotent (bool or NotSet): Include idempotent methods (e.g., GET, PUT).
    - include_non_idempotent (bool or NotSet): Include non-idempotent methods (e.g., POST).
    - include_standard (bool or NotSet): Include standard HTTP methods.
    - include_non_standard (bool or NotSet): Include non-standard HTTP methods.
    - include_having_request_body (bool or NotSet): Include methods that have a request body.
    - include_maybe_having_request_body (bool or NotSet): Include methods that may have a request body.
    - include_not_having_request_body (bool or NotSet): Include methods that do not have a request body.
    - include_having_response_body (bool or NotSet): Include methods that have a response body.
    - include_maybe_having_response_body (bool or NotSet): Include methods that may have a response body.
    - include_not_having_response_body (bool or NotSet): Include methods that do not have a response body.
    - exclude (tuple): Methods to exclude from the parametrization.

    Returns:
    - pytest.mark.parametrize: A pytest parametrize marker with the selected HTTP methods.

    """
    if all(
        param is NotSet
        for param in [
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
        ]
    ):
        include_standard = True

    methods = set()
    _update_methods_set(methods, include_safe, "safe", True)
    _update_methods_set(methods, include_unsafe, "safe", False)
    _update_methods_set(methods, include_idempotent, "idempotent", True)
    _update_methods_set(methods, include_non_idempotent, "idempotent", False)
    if include_standard is True:
        methods |= set(HTTP_METHODS.keys())
    if include_non_standard is True:
        methods |= {"BREW", "REMIX"}
    _update_methods_set(methods, include_having_request_body, "request_body", True)
    _update_methods_set(methods, include_not_having_request_body, "request_body", False)
    _update_methods_set(methods, include_maybe_having_request_body, "request_body", Maybe)
    _update_methods_set(methods, include_having_response_body, "response_body", True)
    _update_methods_set(methods, include_not_having_response_body, "response_body", False)
    _update_methods_set(methods, include_maybe_having_response_body, "response_body", Maybe)

    methods -= set(exclude)

    return pytest.mark.parametrize("method", sorted(methods))
