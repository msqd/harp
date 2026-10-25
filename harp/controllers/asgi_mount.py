import asyncio
from typing import Optional
from urllib.parse import quote

from asgiref.typing import ASGIApplication, ASGISendCallable

from harp import get_logger
from harp.asgi.events import EVENT_CORE_STARTED, EVENT_CORE_STOPPED
from harp.http import AlreadyHandledHttpResponse, HttpRequest, HttpResponse

logger = get_logger(__name__)


class AsgiMountController:
    """
    Controller delegating requests to an ASGI application mounted under a path prefix.

    The application gets the original scope, with the path rewritten relative to the prefix and ``root_path`` extended
    by it, the original ``receive``, and ``send`` unchanged, so responses stream straight through to the client. Websockets
    are not supported.

    With ``lifespan`` (default), the application's lifespan is started and stopped along with the kernel's, once
    :meth:`register` has been called. An application that refuses the lifespan scope is served without it.
    """

    def __init__(self, app: ASGIApplication, *, prefix: str = "", lifespan: bool = True):
        if prefix and (not prefix.startswith("/") or prefix.endswith("/")):
            raise ValueError(f'Mount prefix must start with "/" and not end with one, got "{prefix}".')

        self.app = app
        self.prefix = prefix
        self.lifespan = lifespan

        self._lifespan_inbox: Optional[asyncio.Queue] = None
        self._lifespan_outbox: Optional[asyncio.Queue] = None
        self._lifespan_task: Optional[asyncio.Task] = None

    def __repr__(self):
        return f"{type(self).__name__}({self.prefix or '/'})"

    async def __call__(self, request: HttpRequest, asgi_send: ASGISendCallable) -> HttpResponse:
        scope = request._impl.asgi_scope
        path = scope["path"]

        if self.prefix and path != self.prefix and not path.startswith(self.prefix + "/"):
            return HttpResponse("Not found.", status=404, content_type="text/plain")

        mounted = {
            **scope,
            "path": path[len(self.prefix) :] or "/",
            "root_path": scope.get("root_path", "") + self.prefix,
        }
        raw_path = scope.get("raw_path")
        if raw_path is not None:
            mounted["raw_path"] = self._strip_prefix_from_raw_path(raw_path, mounted["path"])

        await self.app(mounted, request._impl.asgi_receive, asgi_send)
        return AlreadyHandledHttpResponse()

    def _strip_prefix_from_raw_path(self, raw_path: bytes, path: str) -> bytes:
        """The raw path keeps its original encoding when it spells the prefix literally, else it is rebuilt from the
        decoded path (the prefix was matched on it, so it may be percent-encoded in the raw one)."""
        prefix = self.prefix.encode()
        if raw_path == prefix:
            return b"/"
        if raw_path.startswith(prefix + b"/"):
            return raw_path[len(prefix) :]
        return quote(path).encode()

    def register(self, dispatcher):
        """Ties the mounted application's lifespan to the kernel's, through the dispatcher it uses."""
        if self.lifespan:
            dispatcher.add_listener(EVENT_CORE_STARTED, self._on_started)
            dispatcher.add_listener(EVENT_CORE_STOPPED, self._on_stopped)

    async def _on_started(self, event):
        await self.start()

    async def _on_stopped(self, event):
        await self.stop()

    async def start(self):
        if not self.lifespan:
            return

        self._lifespan_inbox, self._lifespan_outbox = asyncio.Queue(), asyncio.Queue()
        scope = {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}, "state": {}}
        self._lifespan_task = asyncio.ensure_future(self._run_lifespan(scope))
        self._lifespan_task.add_done_callback(lambda _: self._lifespan_outbox.put_nowait(None))

        await self._lifespan_inbox.put({"type": "lifespan.startup"})
        message = await self._lifespan_outbox.get()
        if message is None:
            self._lifespan_task.exception()  # retrieved: the refusal is expected, not an unhandled error
            self._lifespan_task = None
            logger.info("Mounted application does not support lifespan.", prefix=self.prefix)
        elif message["type"] == "lifespan.startup.failed":
            self._lifespan_task = None
            raise RuntimeError(f'Mounted application "{self.prefix or "/"}" failed to start: {message.get("message")}')

    async def stop(self):
        """Stops the application. Failures are logged, never raised, so the rest of the shutdown goes on."""
        task, self._lifespan_task = self._lifespan_task, None
        if task is None:
            return

        try:
            if not task.done():
                await self._lifespan_inbox.put({"type": "lifespan.shutdown"})
                await self._lifespan_outbox.get()
            await task
        except Exception:
            logger.exception("Mounted application failed during shutdown.", prefix=self.prefix)

    async def _run_lifespan(self, scope):
        await self.app(scope, self._lifespan_inbox.get, self._lifespan_outbox.put)
