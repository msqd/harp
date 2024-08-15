"""
Proxy Application

"""

import asyncio
from asyncio import TaskGroup

from httpx import AsyncClient

from harp.config import Application
from harp.config.events import OnBoundEvent, OnShutdownEvent

from .settings import ProxySettings

PROXY_HEALTHCHECKS_TASK = "proxy.healthchecks"


async def create_background_task_group(coroutines):
    async def _execute():
        async with TaskGroup() as task_group:
            for coroutine in coroutines:
                task_group.create_task(coroutine)

    return asyncio.create_task(_execute())


async def on_bound(event: OnBoundEvent):
    settings: ProxySettings = event.provider.get(ProxySettings)
    for endpoint in settings.endpoints:
        event.resolver.add(
            endpoint,
            dispatcher=event.dispatcher,
            http_client=event.provider.get(AsyncClient),
        )

    event.provider.set(
        PROXY_HEALTHCHECKS_TASK,
        await create_background_task_group(
            [endpoint.remote.check_forever() for endpoint in settings.endpoints if endpoint.remote.probe is not None]
        ),
    )


async def on_shutdown(event: OnShutdownEvent):
    await event.provider.get(PROXY_HEALTHCHECKS_TASK)._abort()


application = Application(
    dependencies=["services"],
    on_bound=on_bound,
    settings_type=ProxySettings,
)
