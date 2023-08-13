import asyncio

from harp.asgi import get_asgi_app_for_router
from harp.filter import Filter


class Harp:
    def __init__(self):
        self.default_ingress = Filter()
        self.ingresses = [self.default_ingress]
        self.rules = []
        self.mounts = []

    def add_egress(self, endpoint):
        return Filter()

    def add_rule(self, rule):
        self.rules.append(rule)

    def mount(
        self,
        prefix,
        target,
        *,
        scope_filters=(),
        request_filters=(),
        response_filters=(),
    ):
        prefix_length = len(prefix) - 1

        async def _mount_scope_filter(scope):
            scope["remote_path"] = scope["path"][prefix_length:]

        self.mounts.append(
            (
                prefix,
                target,
                (_mount_scope_filter, *scope_filters),
                request_filters,
                response_filters,
            )
        )

    def find_by_scope(self, scope):
        for (
            prefix,
            target,
            scope_filters,
            request_filters,
            response_filters,
        ) in self.mounts:
            if scope["path"].startswith(prefix):
                return target, scope_filters, request_filters, response_filters
        return None, (), (), ()

    # code below should be separated from router

    PORT = 4000

    async def arun_uvicorn(self):
        import uvicorn

        proxy = uvicorn.Server(
            uvicorn.Config(
                get_asgi_app_for_router(self),
                port=self.PORT,
                log_level="info",
                headers=[("server", "harp-proxy/0.1")],
            )
        )
        return await proxy.serve()

    def run_uvicorn(self):
        asyncio.run(self.arun_uvicorn())

    def run(self):
        import asyncio

        import uvloop
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"localhost:{self.PORT}"]

        uvloop.install()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(serve(get_asgi_app_for_router(self), config))
