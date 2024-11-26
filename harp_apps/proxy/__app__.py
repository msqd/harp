"""
Proxy Application

"""

import asyncio
from asyncio import TaskGroup
from typing import cast

from harp.config import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnShutdownEvent
from harp.services.resolvers import ServiceResolver
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
    settings = event.settings.get("proxy")
    # add a controller service instance for each endpoint
    for endpoint in settings.endpoints:
        if endpoint.controller is not None:
            controller = endpoint.controller
            name = f"proxy.controllers.{endpoint.name}_controller"
            resolver = ServiceResolver(event.container, controller.to_service_definition(name, lifestyle="singleton"))
            event.container._map[name] = resolver

    event.container.add_singleton(Proxy, cast(type, ProxyFactory))


async def on_bound(event: OnBoundEvent):
    proxy: Proxy = event.provider.get(Proxy)

    for endpoint in proxy.endpoints:
        name = endpoint.settings.name
        event.provider._map[f"proxy.controllers.{name}_controller"].bind(remote=endpoint.remote, name=name)
        controller = event.provider.get(f"proxy.controllers.{name}_controller")
        event.resolver.add_endpoint(endpoint, controller=controller)

    event.provider.set(
        PROXY_HEALTHCHECKS_TASK,
        await create_background_task_group(
            [
                endpoint.remote.check_forever()
                for endpoint in proxy.endpoints
                if (endpoint.remote and endpoint.remote.probe)
            ]
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
