from http.cookiejar import CookieJar, DefaultCookiePolicy


class NoCookieJar(CookieJar):
    """A proxy relays cookies between clients and upstreams, it never keeps any of its own."""

    def __init__(self):
        super().__init__(policy=DefaultCookiePolicy(allowed_domains=[]))
