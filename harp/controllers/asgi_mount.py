import asyncio
from typing import Optional

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
        if "raw_path" in scope:
            mounted["raw_path"] = scope["raw_path"][len(self.prefix.encode()) :] or b"/"

        await self.app(mounted, request._impl.asgi_receive, asgi_send)
        return AlreadyHandledHttpResponse()

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
            raise RuntimeError(f'Mounted application "{self.prefix or "/"}" failed to start: {message.get("message")}')

    async def stop(self):
        task, self._lifespan_task = self._lifespan_task, None
        if task is None:
            return

        await self._lifespan_inbox.put({"type": "lifespan.shutdown"})
        await self._lifespan_outbox.get()
        await task

    async def _run_lifespan(self, scope):
        await self.app(scope, self._lifespan_inbox.get, self._lifespan_outbox.put)
