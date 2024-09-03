from harp.commandline.server import CommonServerOptions


def test_default():
    options = CommonServerOptions(options=(), files=(), enable=(), disable=())
    assert options.as_list() == []


def test_applications():
    options = CommonServerOptions(options=(), files=(), enable=("foo", "bar"), disable=("baz", "blurp"))
    assert options.as_list() == [
        "--enable foo",
        "--enable bar",
        "--disable baz",
        "--disable blurp",
    ]
