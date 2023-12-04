from .context import AsgiContext


class asgi:
    class http:
        class response:
            @staticmethod
            def start(**kwargs):
                return {"type": "http.response.start", **kwargs}

            @staticmethod
            def body(**kwargs):
                return {"type": "http.response.body", **kwargs}


__all__ = [
    "AsgiContext",
    "asgi",
]
