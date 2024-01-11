from http_router import NotFoundError, Router
from rich.console import Console
from rich.traceback import Traceback

from harp.core.asgi.messages import ASGIRequest, ASGIResponse
from harp.utils.arguments import Arguments


def get_exception_traceback_str(exc):
    console = Console(record=True)
    traceback = Traceback.from_exception(type(exc), exc, exc.__traceback__)
    console.print(traceback)
    return console.export_html()


class RoutingController:
    RouterType = Router
    RouterArguments = Arguments(trim_last_slash=True)

    def __init__(self, *, handle_errors=True, router=None):
        self.router = router or self.create_router()
        self.handle_errors = handle_errors

        self.configure()

    def configure(self):
        pass

    def create_router(self):
        return self.RouterType(*self.RouterArguments.args, *self.RouterArguments.kwargs)

    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        try:
            match = self.router(request.path, method=request.method)
            return await match.target(request, response, **(match.params or {}))
        except NotFoundError as exc:
            if not self.handle_errors:
                raise
            await self.handle_error(exc, response, status=404)
        except Exception as exc:
            if not self.handle_errors:
                raise
            await self.handle_error(exc, response)

    async def handle_error(self, exc, response, *, status=500):
        response.headers["content-type"] = "text/html"
        await response.start(status=status)
        await response.body(f"<h1>{type(exc).__name__}</h1><h2>Stack trace</h2>{get_exception_traceback_str(exc)}")
