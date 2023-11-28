from asgiref.testing import ApplicationCommunicator
from asgiref.typing import LifespanScope, LifespanStartupEvent

from harp import ProxyFactory
from harp.proxy import Proxy
from harp.testing.http_communiator import HttpCommunicator


class TestProxy(Proxy):
    """
    Proxy subclass including utilities for calling asgi tests on itself.

    """

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

    def asgi_http(self, method, path, *, host=None, port=None):
        return HttpCommunicator(
            self,
            method,
            path,
            hostname=host or self.default_host,
            port=port or self.default_port,
        ).get_response()

    def asgi_http_get(self, path, *, host=None, port=None):
        return self.asgi_http("GET", path, host=host, port=port)

    def asgi_http_post(self, path, *, host=None, port=None):
        return self.asgi_http("POST", path, host=host, port=port)


class BaseProxyTest:
    """
    Base class for proxy tests, defining utilities for better readability while writing tests.
    """

    def create_proxy_factory(self, *args, **kwargs):
        return ProxyFactory(*args, ProxyType=TestProxy, **kwargs)
