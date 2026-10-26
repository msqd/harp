"""How the cache application declares its background work."""

from types import SimpleNamespace

import pytest

from harp.services import CannotResolveTypeException
from harp.sweeps import SweepRegistry
from harp_apps.http_cache.__app__ import on_bound
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.records.redis import UnsuitableRedis
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


class RecordsThatRefuse(MemoryCacheRecords):
    async def ready(self):
        raise UnsuitableRedis("the cache cannot start here")


async def test_the_cache_does_not_start_on_records_that_cannot_hold_it():
    sweeps = SweepRegistry()
    services = {"http_cache.storage": AsyncStorage(RecordsThatRefuse())}

    with pytest.raises(UnsuitableRedis, match="cannot start here"):
        await on_bound(SimpleNamespace(sweeps=sweeps, provider=provider(services)))

    assert len(sweeps) == 0
