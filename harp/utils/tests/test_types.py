from harp.utils.types import typeof


def test_typeof():
    assert typeof(1) == "builtins.int"
    assert typeof("1") == "builtins.str"
    assert typeof(1, short=True) == "int"
    assert typeof("1", short=True) == "str"
    assert typeof(object) == "builtins.type"
