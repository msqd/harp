import logging

import pytest
import structlog
import structlog.testing

from harp.asgi import kernel as kernel_module
from harp.asgi.kernel import ASGIKernel


@pytest.fixture(autouse=True)
def logs(monkeypatch):
    """Bind the kernel logger like a running HARP does (filtering ``BoundLogger``, whose ``exception()`` requires an event)."""
    capture = structlog.testing.LogCapture()
    monkeypatch.setattr(
        kernel_module,
        "logger",
        structlog.wrap_logger(
            None,
            processors=[structlog.dev.set_exc_info, structlog.processors.format_exc_info, capture],
            wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        ),
    )
    return capture.entries


class _Resolver:
    def __init__(self, controller):
        self.controller = controller

    async def resolve(self, request):
        return self.controller


async def _call(kernel):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    try:
        await kernel(scope, receive, send)
    except Exception as exc:
        return sent, exc
    return sent, None


def _kernel(controller, **kwargs):
    kernel = ASGIKernel(resolver=_Resolver(controller), **kwargs)
    kernel.started = True
    return kernel


class TestKernelUnhandledControllerException:
    @pytest.mark.asyncio
    async def test_controller_raising_gets_a_500_and_the_error_is_logged_with_traceback(self, logs):
        async def controller():
            raise RuntimeError("boom-marker")

        sent, error = await _call(_kernel(controller))

        assert error is None
        assert [(m["type"], m.get("status")) for m in sent][:1] == [("http.response.start", 500)]
        assert b"Internal Server Error" in b"".join(m.get("body", b"") for m in sent)
        assert [e["log_level"] for e in logs] == ["error"]
        assert "Traceback" in logs[0]["exception"]
        assert "RuntimeError: boom-marker" in logs[0]["exception"]

    @pytest.mark.asyncio
    async def test_exception_after_response_started_is_reraised_without_a_second_start(self, logs):
        async def controller(asgi_send):
            await asgi_send({"type": "http.response.start", "status": 200, "headers": []})
            raise RuntimeError("late-boom")

        sent, error = await _call(_kernel(controller))

        assert isinstance(error, RuntimeError)
        assert [m["type"] for m in sent] == ["http.response.start"]
        assert "RuntimeError: late-boom" in logs[0]["exception"]


class TestKernelDebugErrorPage:
    @pytest.mark.asyncio
    async def test_debug_page_escapes_exception_text_and_traceback(self):
        async def controller():
            raise RuntimeError("<script>alert(1)</script>")

        sent, error = await _call(_kernel(controller, debug=True))

        body = b"".join(m.get("body", b"") for m in sent).decode()
        assert error is None
        assert sent[0]["status"] == 500
        assert "<script>" not in body
        assert "&lt;script&gt;" in body
