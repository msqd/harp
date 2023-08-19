from urllib.parse import urljoin


class ProxyEndpoint:
    def __init__(self, url, *, name=None):
        self.name = name
        self.url = url

    def get_proxy_scope(self, scope):
        return {
            "target": self.url,
            "method": scope["method"],
            "path": scope["raw_path"].decode("utf-8"),
            "query_string": scope["query_string"].decode("utf-8"),
        }

    def contextualize(self, url):
        if url.startswith(self.url):
            return urljoin("/", url[len(self.url) :])
        return url
