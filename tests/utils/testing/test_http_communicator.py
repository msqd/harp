from harp.utils.testing.communicators import HTTPCommunicator


async def _app(scope, receive, send):
    pass


def test_raw_path_keeps_target_as_sent():
    assert HTTPCommunicator(_app, "GET", "//x/a%2Fb").scope["raw_path"] == b"//x/a%2Fb"


def test_path_is_decoded_without_reading_network_location():
    assert HTTPCommunicator(_app, "GET", "//x/a%2Fb").scope["path"] == "//x/a/b"


def test_query_string_is_split_from_raw_path():
    scope = HTTPCommunicator(_app, "GET", "/a%20b?q=%20").scope
    assert (scope["raw_path"], scope["path"], scope["query_string"]) == (b"/a%20b", "/a b", b"q=%20")
