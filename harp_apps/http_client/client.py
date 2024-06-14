from httpx import AsyncClient

from harp_apps.http_client.settings import HttpClientSettings


class AsyncHttpClient(AsyncClient):
    settings: HttpClientSettings

    def __init__(self, settings: HttpClientSettings):
        transport = settings.transport.build()

        if settings.cache.enabled:
            transport = settings.cache.transport.build(
                transport=transport,
                controller=settings.cache.controller.build(),
                storage=settings.cache.storage.build(),
            )

        super().__init__(transport=transport, timeout=settings.timeout)
