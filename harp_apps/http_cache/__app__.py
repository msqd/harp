import sys
from os.path import dirname

from pathlib import Path

from harp.config import Application, OnBindEvent
from harp.config.events import OnBoundEvent
from harp.services import CannotResolveTypeException
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
    """Have the janitor reclaim the bans (ADR-0014), if it is loaded: otherwise the storage sweeps by itself."""
    # The janitor is not a dependency of this application: its module is there only when the application is loaded.
    janitor_module = sys.modules.get("harp_apps.janitor.worker")
    if janitor_module is None:
        return
    try:
        janitor = event.provider.get(janitor_module.JanitorWorker)
    except CannotResolveTypeException:
        return
    storage = event.provider.get("http_cache.storage")
    if isinstance(storage, AsyncStorage):
        janitor.sweeps.append(storage.delegate_reclamation())


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
    settings_type=HttpCacheSettings,
    dependencies=["http_client"],
)
