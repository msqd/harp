"""How the cache application hands its background work to the janitor."""

from types import SimpleNamespace

from harp.config import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.services import CannotResolveTypeException
from harp_apps.http_cache.__app__ import on_bound
from harp_apps.http_cache.records import BanMode, MemoryCacheRecords
from harp_apps.http_cache.settings import ReclamationSettings
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.janitor.worker import JanitorWorker


def provider(services):
    def get(key):
        if key not in services:
            raise CannotResolveTypeException(key)
        return services[key]

    return SimpleNamespace(get=get)


async def test_the_cache_hands_its_reclamation_to_the_janitor():
    janitor, storage = SimpleNamespace(sweeps=[]), AsyncStorage(MemoryCacheRecords())

    await on_bound(SimpleNamespace(provider=provider({JanitorWorker: janitor, "http_cache.storage": storage})))

    assert janitor.sweeps == [storage.reclaim]


async def test_the_janitor_of_a_system_runs_the_reclamation_of_its_cache(tmp_path):
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": f"sqlite+aiosqlite:///{tmp_path}/harp.db"}})
    builder.applications.add("http_cache")
    system = await SystemBuilder(builder.applications, builder.build()).abuild()
    try:
        storage = system.provider.get("http_cache.storage")

        assert storage.reclaim in system.provider.get(JanitorWorker).sweeps
        assert storage._reclamation == ReclamationSettings()
    finally:
        await system.dispose()


async def test_without_a_janitor_the_storage_reclaims_by_itself():
    records = MemoryCacheRecords()
    storage = AsyncStorage(records, reclamation=ReclamationSettings(grace=0))
    await storage.invalidate_prefix("api", "/users", mode=BanMode.HARD)

    await on_bound(SimpleNamespace(provider=provider({"http_cache.storage": storage})))
    await storage._sweep()

    assert await records.bans() == []


async def test_a_storage_of_another_make_is_left_alone():
    janitor = SimpleNamespace(sweeps=[])

    await on_bound(SimpleNamespace(provider=provider({JanitorWorker: janitor, "http_cache.storage": object()})))

    assert janitor.sweeps == []
