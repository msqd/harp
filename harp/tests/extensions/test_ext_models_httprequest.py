from datetime import datetime

from harp._harp import HttpRequest


def test_base():
    req = HttpRequest()
    assert req.protocol == "http"
    assert req.kind == "request"
    print(req.created_at)
    print(type(req.created_at))

    now = datetime(2021, 1, 1)
    req = HttpRequest(created_at=now)
    assert req.protocol == "http"
    assert req.kind == "request"
    print(req.created_at)
    print(type(req.created_at))
    assert req.created_at is now
