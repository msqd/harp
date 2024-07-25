from config.common import merge_values


def test_merge_values_first_level():
    a = {"rules": {"a": 1, "b": 2}}
    b = {"rules": {"b": 3, "c": 4}}

    merge_values(a, b)
    assert a == {"rules": {"a": 1, "b": 3, "c": 4}}


def test_merge_values_deep_list():
    a = {"rules": {"*": {"*": ["foo"]}}}
    b = {"rules": {"*": {"*": "bar"}}}

    merge_values(a, b)
    assert a == {"rules": {"*": {"*": "bar"}}}
