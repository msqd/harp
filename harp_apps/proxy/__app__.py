"""
Proxy Application

"""

import asyncio
from asyncio import TaskGroup
from typing import cast

from httpx import AsyncClient

from harp.config import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnShutdownEvent
from harp.utils.services import factory

from .settings import Proxy, ProxySettings

PROXY_HEALTHCHECKS_TASK = "proxy.healthchecks"


@factory(Proxy)
def ProxyFactory(self, settings: ProxySettings) -> Proxy:
    return Proxy(settings=settings)


async def create_background_task_group(coroutines):
    async def _execute():
        async with TaskGroup() as task_group:
            for coroutine in coroutines:
                task_group.create_task(coroutine)

    return asyncio.create_task(_execute())


async def on_bind(event: OnBindEvent):
    event.container.add_singleton(Proxy, cast(type, ProxyFactory))


async def on_bound(event: OnBoundEvent):
    proxy: Proxy = event.provider.get(Proxy)
    http_client: AsyncClient = event.provider.get(AsyncClient)

    for endpoint in proxy.endpoints:
        event.resolver.add(endpoint, dispatcher=event.dispatcher, http_client=http_client)

    event.provider.set(
        PROXY_HEALTHCHECKS_TASK,
        await create_background_task_group(
            [endpoint.remote.check_forever() for endpoint in proxy.endpoints if endpoint.remote.probe is not None]
        ),
    )


async def on_shutdown(event: OnShutdownEvent):
    await event.provider.get(PROXY_HEALTHCHECKS_TASK)._abort()


application = Application(
    dependencies=["services"],
    on_bind=on_bind,
    on_bound=on_bound,
    settings_type=ProxySettings,
)
