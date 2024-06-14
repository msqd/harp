from harp_apps.dashboard.filters.utils import str_to_float_or_none


def test_str_to_float_or_none():
    assert str_to_float_or_none("123.45") == 123.45
    assert str_to_float_or_none("0") == 0.0
    assert str_to_float_or_none("-123.45") == -123.45
    assert str_to_float_or_none("not a number") is None
    assert str_to_float_or_none("") is None
