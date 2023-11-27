from harp.proxy import Proxy
from harp.testing.http_communiator import HttpCommunicator


class TestProxy(Proxy):
    def get(self, path, *, port=None):
        return HttpCommunicator(self, "GET", path, port=port)
