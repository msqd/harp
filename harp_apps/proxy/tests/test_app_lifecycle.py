"""Lifecycle tests for the proxy application (shutdown of healthcheck background tasks)."""

import asyncio

from harp.config.events import OnShutdownEvent
from harp_apps.proxy.__app__ import PROXY_HEALTHCHECKS_TASK, application, on_shutdown


def test_application_registers_on_shutdown_handler():
    # Regression: on_shutdown must be wired into the Application, otherwise the healthcheck
    # background tasks are never cancelled and leak on every teardown.
    assert application.on_shutdown is on_shutdown


class _StubProvider:
    def __init__(self, services):
        self._services = services

    def get(self, name):
        return self._services[name]


async def test_on_shutdown_cancels_the_healthchecks_task():
    # The healthcheck task group runs forever; shutdown must cancel it cleanly (not crash).
    task = asyncio.create_task(asyncio.sleep(3600))
    event = OnShutdownEvent(None, _StubProvider({PROXY_HEALTHCHECKS_TASK: task}))

    await on_shutdown(event)

    assert task.cancelled()
