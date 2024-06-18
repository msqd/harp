from unittest.mock import patch

import pytest

from harp.utils.env import cast_bool, get_bool_from_env

parametrize_with_string_booleans = pytest.mark.parametrize(
    "value, expected",
    [
        ("true", True),
        ("yes", True),
        ("1", True),
        ("false", False),
        ("no", False),
        ("0", False),
    ],
)


@parametrize_with_string_booleans
def test_cast_bool(value, expected):
    assert cast_bool(value) == expected


@parametrize_with_string_booleans
def test_get_bool_from_env(value, expected):
    with patch.dict("os.environ", {"TEST_ENV_VAR": value}):
        assert get_bool_from_env("TEST_ENV_VAR", False) == expected
