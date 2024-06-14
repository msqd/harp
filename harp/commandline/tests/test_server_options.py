from harp.commandline.server import CommonServerOptions


def test_default():
    options = CommonServerOptions(options=(), files=(), enable=(), disable=(), reset=False)
    assert options.as_list() == []


def test_applications():
    options = CommonServerOptions(options=(), files=(), enable=("foo", "bar"), disable=("baz", "blurp"), reset=False)
    assert options.as_list() == ["--enable foo", "--enable bar", "--disable baz", "--disable blurp"]


def test_reset():
    options = CommonServerOptions(options=(), files=(), enable=(), disable=(), reset=True)
    assert options.as_list() == [
        "--set storage.drop_tables=true",
    ]
