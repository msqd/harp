import hashlib

import pytest

from harp.utils.collections import all_combinations
from harp.utils.testing.http import parametrize_with_http_methods


@pytest.mark.parametrize(
    "parameters",
    list(
        sorted(
            all_combinations(
                [
                    "include_safe",
                    "include_unsafe",
                    "include_idempotent",
                    "include_non_idempotent",
                    "include_standard",
                    "include_non_standard",
                    "include_having_request_body",
                    "include_maybe_having_request_body",
                    "include_not_having_request_body",
                    "include_having_response_body",
                    "include_maybe_having_response_body",
                    "include_not_having_response_body",
                ],
                maxlen=3,
            ),
        )
    ),
    ids=lambda x: hashlib.md5(",".join(sorted(x)).encode()).hexdigest()[:7],
)
def test_methods(snapshot, parameters):
    p = parametrize_with_http_methods(**{k: True for k in parameters})
    assert snapshot == ",".join(sorted(parameters)) + " => " + ",".join(sorted(p.args[1]))
