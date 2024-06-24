from httpx import AsyncClient

from harp_apps.http_client.settings import HttpClientSettings


def _resolve(x, *args, **kwargs):
    if hasattr(x, "build"):
        return x.build(*args, **kwargs)
    if len(args) or len(kwargs):
        raise ValueError(
            f"Cannot resolve {x} with args {args} and kwargs {kwargs}: parametrized lazy services must implement a build method."
        )
    return x


class AsyncHttpClient(AsyncClient):
    settings: HttpClientSettings

    def __init__(self, settings: HttpClientSettings):
        transport = _resolve(settings.transport)

        if settings.cache.enabled:
            transport = _resolve(
                settings.cache.transport,
                transport=transport,
                controller=_resolve(settings.cache.controller),
                storage=_resolve(settings.cache.storage),
            )

        super().__init__(transport=transport, timeout=settings.timeout)
