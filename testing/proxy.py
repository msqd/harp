from asgiref.testing import ApplicationCommunicator
from asgiref.typing import LifespanScope, LifespanStartupEvent

from harp.proxy import Proxy
from harp.testing.http_communiator import HttpCommunicator


class TestProxy(Proxy):
    default_host = "localhost"
    default_port = 80

    def __init__(self, *, endpoints, container, default_host=None, default_port=None):
        super().__init__(endpoints=endpoints, container=container)
        self.default_host = default_host or self.default_host
        self.default_port = default_port or self.default_port

    async def asgi_lifespan_startup(self):
        com = ApplicationCommunicator(
            self,
            LifespanScope(
                type="lifespan",
                asgi={"version": "3.0", "spec_version": "2.0"},
            ),
        )
        await com.send_input(
            LifespanStartupEvent(type="lifespan.startup"),
        )
        await com.wait()

    async def asgi_http_get(self, path, *, host=None, port=None):
        com = HttpCommunicator(
            self,
            "GET",
            path,
            hostname=host or self.default_host,
            port=port or self.default_port,
        )
        return await com.get_response()
