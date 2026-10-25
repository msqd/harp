from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from harp.config import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.config.defaults import DEFAULT_APPLICATIONS
from harp.errors import MissingDependencyError
from harp.unit_of_work import IUnitOfWorkFactory, TransactionalEventDispatcher, auditable
from harp.unit_of_work.audit import AuditableEvent
from harp_apps.audit.__app__ import on_bound
from harp_apps.audit.models import AuditEvent
from harp_apps.audit.settings import AuditSettings
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.types import IStorage


@auditable("test.needy_acted")
class NeedyActed(AuditableEvent):
    pass


def configuration(*applications: str):
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    builder.applications.remove("janitor")  # its background sweep fights the test over the in-memory connection
    for name in applications:
        builder.applications.add(name)
    builder.applications.add("harp_apps.audit.tests.needy")
    return builder


def test_audit_is_not_a_default_application():
    assert "audit" not in DEFAULT_APPLICATIONS


async def test_a_harp_without_an_application_depending_on_audit_loads_no_audit():
    builder = ConfigurationBuilder(use_default_applications=False)
    builder.add_values({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    builder.applications.add("storage")

    assert "audit" not in builder.applications


async def test_the_dashboard_loads_the_audit_with_the_default_applications():
    builder = ConfigurationBuilder()

    assert "audit" in builder.applications


async def test_an_application_depending_on_audit_loads_it_when_dependencies_are_autoloaded():
    builder = ConfigurationBuilder(use_default_applications=False)
    builder.add_values({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})

    builder.applications.add("harp_apps.audit.tests.needy", autoload_dependencies=True)

    assert "audit" in builder.applications

    builder.applications.remove("harp_apps.audit.tests.needy")

    assert "audit" not in builder.applications


async def test_an_application_depending_on_audit_needs_it_enabled():
    builder = configuration()
    builder.applications.remove("dashboard")  # the dashboard needs the audit itself, and brings it along
    builder.applications.remove("audit")

    with pytest.raises(MissingDependencyError, match="'harp_apps.audit.tests.needy' requires 'audit'"):
        await SystemBuilder(builder.applications, builder.build()).abuild()


async def test_an_application_depending_on_audit_gets_its_events_recorded():
    builder = configuration("audit")
    system = await SystemBuilder(builder.applications, builder.build()).abuild()
    try:
        assert system.provider.get(AuditSettings).retention_days == 365

        async with system.provider.get(IUnitOfWorkFactory)() as uow:
            await uow.record(NeedyActed())

        async with system.provider.get(IStorage).session_factory() as session:
            assert (await session.execute(select(func.count()).select_from(AuditEvent))).scalar_one() == 1
    finally:
        await system.dispose()


async def test_audit_hands_its_retention_sweep_to_the_janitor():
    janitor = SimpleNamespace(sweeps=[])
    services = {
        TransactionalEventDispatcher: TransactionalEventDispatcher(),
        JanitorWorker: janitor,
        IStorage: object(),
        AuditSettings: AuditSettings(),
    }

    await on_bound(SimpleNamespace(provider=SimpleNamespace(get=services.__getitem__)))

    assert len(janitor.sweeps) == 1
