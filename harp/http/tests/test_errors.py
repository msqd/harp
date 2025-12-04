import harp
from harp.http.errors import HttpError


class TestHttpErrorBody:
    def test_body_returns_message_when_no_exception(self):
        error = HttpError("Something went wrong")
        assert error.body == b"Something went wrong"

    def test_body_returns_exception_type_and_message(self):
        error = HttpError("Error", exception=ValueError("invalid value"))
        assert error.body == b"ValueError: invalid value"

    def test_body_returns_exception_type_only_when_no_message(self):
        error = HttpError("Error", exception=ValueError())
        assert error.body == b"ValueError"

    def test_body_includes_traceback_when_debug_enabled(self, monkeypatch):
        monkeypatch.setattr(harp, "DEBUG", True)
        try:
            raise ValueError("test error")
        except ValueError as e:
            error = HttpError("Error", exception=e)
            body = error.body.decode()
            assert "ValueError: test error" in body
            assert "Traceback" in body
            assert "raise ValueError" in body

    def test_body_excludes_traceback_when_debug_disabled(self, monkeypatch):
        monkeypatch.setattr(harp, "DEBUG", False)
        try:
            raise ValueError("test error")
        except ValueError as e:
            error = HttpError("Error", exception=e)
            body = error.body.decode()
            assert body == "ValueError: test error"
            assert "Traceback" not in body
