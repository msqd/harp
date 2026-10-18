import gc
from types import SimpleNamespace

import pytest

import harp


class Builder:
    async def abuild_system(self):
        async def dispose():
            pass

        return SimpleNamespace(dispose=dispose)


@pytest.fixture(autouse=True)
def unfrozen():
    gc.unfreeze()
    yield
    gc.unfreeze()


async def test_what_exists_at_startup_is_kept_out_of_the_collections_while_serving(monkeypatch):
    seen = {}

    class Adapter:
        def __init__(self, system):
            pass

        async def serve(self):
            seen["frozen"] = gc.get_freeze_count()

    monkeypatch.setattr("harp.config.adapters.get_server", lambda name: SimpleNamespace(adapter_type=Adapter))

    await harp.arun(Builder())

    assert seen["frozen"] > 1000
