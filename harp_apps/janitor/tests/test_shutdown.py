"""The janitor is gone when the system is disposed, not left cancelling against a closed database."""

import asyncio

from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp_apps.janitor.__app__ import JANITOR_WORKER_TASK


async def test_the_worker_task_is_over_once_the_system_is_disposed():
    builder = ConfigurationBuilder(use_default_applications=False)
    for app in ("storage", "janitor"):
        builder.applications.add(app, autoload_dependencies=True)
    builder.add_values({"storage": {"url": "sqlite:///:memory:"}})
    system = await SystemBuilder(builder.applications, builder.build()).abuild()
    task = system.provider.get(JANITOR_WORKER_TASK)
    await asyncio.sleep(0.05)  # let it start its first sweep

    await system.dispose()

    assert task.done()
