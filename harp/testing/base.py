from harp import ProxyFactory
from testing.proxy import TestProxy


class BaseProxyTest:
    def factory(self, *args, **kwargs):
        return ProxyFactory(*args, ProxyType=TestProxy, **kwargs)
