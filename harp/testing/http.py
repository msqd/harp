import pytest

from harp.models.http import HTTP_METHODS
from harp.types import _not_set


def parametrize_with_http_methods(
    *,
    include_safe=_not_set,
    include_unsafe=_not_set,
    include_idempotent=_not_set,
    include_non_idempotent=_not_set,
    include_standard=True,
    include_non_standard=_not_set,
    exclude=(),
):
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

    methods -= set(exclude)

    return pytest.mark.parametrize("method", list(sorted(methods)))
