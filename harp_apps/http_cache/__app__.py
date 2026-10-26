from os.path import dirname

from pathlib import Path

from harp.config import Application, OnBindEvent
from harp.config.events import OnBoundEvent
from .settings import HttpCacheSettings
from .storages import AsyncStorage


async def on_bind(event: OnBindEvent):
    settings = event.settings["http_cache"]

    # Load service definitions, bound to our settings.
    event.container.load(
        Path(dirname(__file__)) / "services.yml",
        bind_settings=settings,
    )
    if "storage" in event.settings:
        event.container.load(Path(dirname(__file__)) / "services_sql.yml", bind_settings=settings)

    # WORKAROUND: Manually override http_client's transport
    # until cross-app service overrides are supported (issue #806)
    from httpx import AsyncClient

    from harp.services.references import LazyServiceReference

    # Get the http_client service from container by type
    http_client_resolver = event.container._map.get(AsyncClient)

    if http_client_resolver and hasattr(http_client_resolver, "service"):
        # Update the http_client service's defaults to use cache transport
        service = http_client_resolver.service
        if not hasattr(service, "defaults"):
            service.defaults = {}
        # Override the transport argument to use http_cache.transport
        # This inserts the cache layer between http_client and proxy_transport
        service.defaults["transport"] = LazyServiceReference(target="http_cache.transport")


async def on_bound(event: OnBoundEvent):
    """Declare the periodic maintenance of the cache (ADR-0014): the janitor schedules it, the storage runs none."""
    storage = event.provider.get("http_cache.storage")
    if isinstance(storage, AsyncStorage):
        for sweep in storage.sweeps():
            event.sweeps.declare(sweep)


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
    settings_type=HttpCacheSettings,
    dependencies=["http_client"],
)
