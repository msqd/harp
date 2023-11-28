from harp import ProxyFactory
from testing.proxy import TestProxy


class BaseProxyTest:
    def create_proxy_factory(self, *args, **kwargs):
        return ProxyFactory(*args, ProxyType=TestProxy, **kwargs)
