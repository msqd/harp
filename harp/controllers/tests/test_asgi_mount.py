import asyncio

import pytest
from asgiref.testing import ApplicationCommunicator
from whistle import AsyncEventDispatcher

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.asgi.events import EVENT_CORE_STOPPED
from harp.asgi.kernel import ASGIKernel
from harp.controllers import AsgiMountController
from harp.http import AlreadyHandledHttpResponse, HttpRequest


def _scope(path="/mcp/messages", **extra):
    return {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"a=1",
        "headers": [],
        "server": ("localhost", 80),
        **extra,
    }


def _request(scope, receive=None):
    async def default_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return HttpRequest(HttpRequestAsgiBridge(scope, receive or default_receive))


class Recorder:
    """ASGI application recording the scope it gets and the messages it receives, answering in two chunks."""

    def __init__(self):
        self.scope = None
        self.received = []

    async def __call__(self, scope, receive, send):
        self.scope = scope
        message = await receive()
        self.received.append(message)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"one", "more_body": True})
        await send({"type": "http.response.body", "body": b"two", "more_body": False})


class TestMountedRequests:
    async def test_app_gets_the_scope_under_the_prefix(self):
        app = Recorder()

        await AsgiMountController(app, prefix="/mcp")(_request(_scope()), _Sink())

        assert app.scope["path"] == "/messages"
        assert app.scope["raw_path"] == b"/messages"
        assert app.scope["root_path"] == "/mcp"
        assert app.scope["method"] == "POST"
        assert app.scope["query_string"] == b"a=1"

    async def test_root_path_extends_the_one_already_in_scope(self):
        app = Recorder()

        await AsgiMountController(app, prefix="/mcp")(_request(_scope(root_path="/base")), _Sink())

        assert app.scope["root_path"] == "/base/mcp"

    async def test_prefix_itself_maps_to_root(self):
        app = Recorder()

        await AsgiMountController(app, prefix="/mcp")(_request(_scope("/mcp")), _Sink())

        assert app.scope["path"] == "/"

    async def test_percent_encoded_prefix_is_matched_on_the_decoded_path(self):
        app = Recorder()
        scope = {**_scope("/mcp/x"), "raw_path": b"/m%63p/x"}

        await AsgiMountController(app, prefix="/mcp")(_request(scope), _Sink())

        assert app.scope["path"] == "/x"
        assert app.scope["raw_path"] == b"/x"

    async def test_raw_path_keeps_its_encoding_after_the_prefix(self):
        app = Recorder()
        scope = {**_scope("/mcp/a b"), "raw_path": b"/mcp/a%20b"}

        await AsgiMountController(app, prefix="/mcp")(_request(scope), _Sink())

        assert app.scope["path"] == "/a b"
        assert app.scope["raw_path"] == b"/a%20b"

    async def test_missing_raw_path_is_fine(self):
        app = Recorder()
        scope = _scope()
        del scope["raw_path"]

        await AsgiMountController(app, prefix="/mcp")(_request(scope), _Sink())

        assert app.scope["path"] == "/messages"
        assert "raw_path" not in app.scope

    async def test_empty_prefix_leaves_the_path_alone(self):
        app = Recorder()

        await AsgiMountController(app)(_request(_scope("/a/b")), _Sink())

        assert app.scope["path"] == "/a/b"
        assert app.scope["root_path"] == ""

    async def test_path_outside_the_prefix_is_not_found(self):
        app = Recorder()

        response = await AsgiMountController(app, prefix="/mcp")(_request(_scope("/mcpx/a")), _Sink())

        assert response.status == 404
        assert app.scope is None

    async def test_receive_and_send_pass_through_and_responses_stream(self):
        app = Recorder()
        sink = _Sink()
        body = {"type": "http.request", "body": b"hello", "more_body": False}

        async def receive():
            return body

        response = await AsgiMountController(app, prefix="/mcp")(_request(_scope(), receive), sink)

        assert isinstance(response, AlreadyHandledHttpResponse)
        assert app.received == [body]
        assert [m.get("body") for m in sink.messages] == [None, b"one", b"two"]
        assert [m.get("more_body") for m in sink.messages[1:]] == [True, False]


class _Sink:
    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)


class LifespanApp:
    def __init__(self):
        self.events = []

    async def __call__(self, scope, receive, send):
        assert scope["type"] == "lifespan"
        while True:
            message = await receive()
            self.events.append(message["type"])
            await send({"type": message["type"] + ".complete"})
            if message["type"] == "lifespan.shutdown":
                return


async def _refuses_lifespan(scope, receive, send):
    raise RuntimeError("no lifespan here")


class TestMountedLifespan:
    async def test_start_and_stop_drive_the_app_lifespan(self):
        app = LifespanApp()
        mount = AsgiMountController(app, prefix="/mcp")

        await mount.start()
        assert app.events == ["lifespan.startup"]

        await mount.stop()
        assert app.events == ["lifespan.startup", "lifespan.shutdown"]

    async def test_app_without_lifespan_support_still_starts_and_stops(self):
        mount = AsgiMountController(_refuses_lifespan, prefix="/mcp")

        await mount.start()
        await mount.stop()

    async def test_lifespan_can_be_turned_off(self):
        app = LifespanApp()
        mount = AsgiMountController(app, prefix="/mcp", lifespan=False)

        await mount.start()
        await mount.stop()

        assert app.events == []

    async def test_kernel_starts_and_stops_mounted_apps_with_its_own_lifespan(self):
        app = LifespanApp()
        kernel = ASGIKernel(dispatcher=AsyncEventDispatcher())
        AsgiMountController(app, prefix="/mcp").register(kernel.dispatcher)

        com = ApplicationCommunicator(kernel, {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.1"}})
        await com.send_input({"type": "lifespan.startup"})
        assert (await com.receive_output(1))["type"] == "lifespan.startup.complete"
        assert app.events == ["lifespan.startup"]

        await com.send_input({"type": "lifespan.shutdown"})
        assert (await com.receive_output(1))["type"] == "lifespan.shutdown.complete"
        assert app.events == ["lifespan.startup", "lifespan.shutdown"]
        await asyncio.wait_for(com.wait(), 1)

    async def test_kernel_without_mounts_completes_startup_then_shutdown(self):
        com = _lifespan_communicator(ASGIKernel(dispatcher=AsyncEventDispatcher()))

        await com.send_input({"type": "lifespan.startup"})
        assert (await com.receive_output(1))["type"] == "lifespan.startup.complete"

        await com.send_input({"type": "lifespan.shutdown"})
        assert (await com.receive_output(1))["type"] == "lifespan.shutdown.complete"
        await asyncio.wait_for(com.wait(), 1)

    async def test_mounted_app_failing_to_start_fails_the_kernel_startup(self):
        kernel = ASGIKernel(dispatcher=AsyncEventDispatcher())
        AsgiMountController(_fails_to_start, prefix="/mcp").register(kernel.dispatcher)
        com = _lifespan_communicator(kernel)

        await com.send_input({"type": "lifespan.startup"})
        message = await com.receive_output(1)

        assert message["type"] == "lifespan.startup.failed"
        assert "boom" in message["message"]

    async def test_kernel_reports_a_failing_stopped_listener(self):
        kernel = ASGIKernel(dispatcher=AsyncEventDispatcher())

        async def fail(event):
            raise ValueError("stuck")

        kernel.dispatcher.add_listener(EVENT_CORE_STOPPED, fail)
        com = _lifespan_communicator(kernel)
        await com.send_input({"type": "lifespan.startup"})
        await com.receive_output(1)

        await com.send_input({"type": "lifespan.shutdown"})
        message = await com.receive_output(1)

        assert message["type"] == "lifespan.shutdown.failed"
        assert "stuck" in message["message"]

    async def test_mounted_app_crashing_after_startup_does_not_break_shutdown(self):
        kernel = ASGIKernel(dispatcher=AsyncEventDispatcher())
        healthy = LifespanApp()
        AsgiMountController(_crashes_after_start, prefix="/a").register(kernel.dispatcher)
        AsgiMountController(healthy, prefix="/b").register(kernel.dispatcher)
        com = _lifespan_communicator(kernel)
        await com.send_input({"type": "lifespan.startup"})
        assert (await com.receive_output(1))["type"] == "lifespan.startup.complete"
        await asyncio.sleep(0)

        await com.send_input({"type": "lifespan.shutdown"})

        assert (await com.receive_output(1))["type"] == "lifespan.shutdown.complete"
        assert healthy.events == ["lifespan.startup", "lifespan.shutdown"]


def _lifespan_communicator(kernel):
    return ApplicationCommunicator(kernel, {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.1"}})


async def _fails_to_start(scope, receive, send):
    await receive()
    await send({"type": "lifespan.startup.failed", "message": "boom"})


async def _crashes_after_start(scope, receive, send):
    await receive()
    await send({"type": "lifespan.startup.complete"})
    raise RuntimeError("crashed")


@pytest.mark.parametrize("prefix", ["mcp", "/mcp/"])
def test_prefix_is_validated(prefix):
    with pytest.raises(ValueError):
        AsgiMountController(Recorder(), prefix=prefix)
