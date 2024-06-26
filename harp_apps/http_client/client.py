from httpx import AsyncClient
from whistle import IAsyncEventDispatcher

from harp_apps.http_client.settings import HttpClientSettings
from harp_apps.http_client.transport import AsyncFilterableTransport


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

    def __init__(self, settings: HttpClientSettings, dispatcher: IAsyncEventDispatcher):
        self._dispatcher = dispatcher

        transport = _resolve(settings.transport)
        transport = AsyncFilterableTransport(transport=transport, dispatcher=dispatcher)

        if settings.cache.enabled:
            transport = _resolve(
                settings.cache.transport,
                transport=transport,
                controller=_resolve(settings.cache.controller),
                storage=_resolve(settings.cache.storage),
            )

        super().__init__(transport=transport, timeout=settings.timeout)

    @property
    def dispatcher(self):
        return self._dispatcher
