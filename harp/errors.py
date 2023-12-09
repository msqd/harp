class ProxyError(Exception):
    pass


class ProxyConfigurationError(ProxyError):
    pass


class EndpointNotFound(ProxyError):
    pass
