from os.path import dirname

from pathlib import Path

from harp import get_logger
from harp.config import Application, OnBindEvent
from .settings import HttpCacheSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    settings = event.settings["http_cache"]

    # Load service definitions, bound to our settings.
    event.container.load(
        Path(dirname(__file__)) / "services.yml",
        bind_settings=settings,
    )

    # WORKAROUND: Manually override http_client transport until cross-app service
    # overrides are supported (issue #806)
    # Only apply if http_cache is enabled
    if settings.enabled:
        # Get the http_client resolver from container
        from httpx import AsyncClient
        from harp.services.references import LazyServiceReference

        http_client_resolver = event.container._map.get(AsyncClient)

        if http_client_resolver and hasattr(http_client_resolver, "service"):
            # Update the service's defaults to use cache transport
            service = http_client_resolver.service
            if not hasattr(service, "defaults"):
                service.defaults = {}
            # Reference the cache transport by name
            # This will be resolved when the container builds the provider
            service.defaults["transport"] = LazyServiceReference(target="http_cache.transport")


application = Application(
    on_bind=on_bind,
    settings_type=HttpCacheSettings,
    dependencies=["http_client"],
)
