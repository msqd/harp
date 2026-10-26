"""How the cache application declares its background work."""

from types import SimpleNamespace

from harp.services import CannotResolveTypeException
from harp.sweeps import SweepRegistry
from harp_apps.http_cache.__app__ import on_bound
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.storages import AsyncStorage


def provider(services):
    def get(key):
        if key not in services:
            raise CannotResolveTypeException(key)
        return services[key]

    return SimpleNamespace(get=get)


async def test_the_cache_declares_the_sweeps_of_its_storage():
    sweeps, storage = SweepRegistry(), AsyncStorage(MemoryCacheRecords())

    await on_bound(SimpleNamespace(sweeps=sweeps, provider=provider({"http_cache.storage": storage})))

    assert [sweep.name for sweep in sweeps] == [sweep.name for sweep in storage.sweeps()]


async def test_a_storage_of_another_make_is_left_alone():
    sweeps = SweepRegistry()

    await on_bound(SimpleNamespace(sweeps=sweeps, provider=provider({"http_cache.storage": object()})))

    assert len(sweeps) == 0
