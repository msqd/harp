import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from whistle import Event

from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.config import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.unit_of_work import IUnitOfWorkFactory, TransactionalEventDispatcher, auditable
from harp_apps.storage.unit_of_work import SqlUnitOfWorkFactory, current_session


@auditable("test.noted")
class Noted(Event):
    def __init__(self, note: str):
        super().__init__()
        self.note = note


@pytest.fixture
async def session_factory(sql_engine):
    async with sql_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE uow_probe (note VARCHAR(50))"))
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def transactional():
    return TransactionalEventDispatcher()


@pytest.fixture
def dispatcher():
    return LoggingAsyncEventDispatcher()


@pytest.fixture
def unit_of_work(session_factory, transactional, dispatcher):
    return SqlUnitOfWorkFactory(session_factory, transactional=transactional, dispatcher=dispatcher)


async def notes(session_factory) -> list[str]:
    async with session_factory() as session:
        return [row[0] for row in await session.execute(text("SELECT note FROM uow_probe ORDER BY note"))]


async def write_note(event: Noted):
    await current_session().execute(text("INSERT INTO uow_probe (note) VALUES (:note)"), {"note": event.note})


async def test_transactional_listener_write_joins_the_commit(unit_of_work, transactional, session_factory):
    transactional.add_listener("test.noted", write_note)

    async with unit_of_work() as uow:
        await current_session().execute(text("INSERT INTO uow_probe (note) VALUES ('action')"))
        await uow.record(Noted("audit"))

    assert await notes(session_factory) == ["action", "audit"]


async def test_nothing_is_visible_before_the_commit(unit_of_work, transactional, session_factory, sql_engine):
    if sql_engine.dialect.name == "sqlite":
        pytest.skip("the in-memory SQLite pool has a single connection: no concurrent reader")

    transactional.add_listener("test.noted", write_note)
    seen_inside = []

    async with unit_of_work() as uow:
        await uow.record(Noted("audit"))
        seen_inside = await notes(session_factory)

    assert seen_inside == []
    assert await notes(session_factory) == ["audit"]


async def test_failing_transactional_listener_rolls_back_the_action(unit_of_work, transactional, session_factory):
    async def write_then_fail(event: Noted):
        await write_note(event)
        raise ValueError("audit failed")

    transactional.add_listener("test.noted", write_then_fail)

    with pytest.raises(ValueError, match="audit failed"):
        async with unit_of_work() as uow:
            await current_session().execute(text("INSERT INTO uow_probe (note) VALUES ('action')"))
            await uow.record(Noted("audit"))

    assert await notes(session_factory) == []


async def test_failing_action_leaves_nothing(unit_of_work, transactional, session_factory):
    transactional.add_listener("test.noted", write_note)

    with pytest.raises(RuntimeError, match="action failed"):
        async with unit_of_work() as uow:
            await uow.record(Noted("audit"))

            async def action():
                raise RuntimeError("action failed")

            await uow.act(action)

    assert await notes(session_factory) == []


async def test_ordinary_listener_runs_after_the_commit_and_its_failure_changes_nothing(
    unit_of_work, transactional, dispatcher, session_factory
):
    transactional.add_listener("test.noted", write_note)
    visible_to_ordinary_listener = []

    async def ordinary(event: Noted):
        visible_to_ordinary_listener.extend(await notes(session_factory))
        raise ValueError("webhook down")

    dispatcher.add_listener("test.noted", ordinary)

    async with unit_of_work() as uow:
        await uow.record(Noted("audit"))

    assert visible_to_ordinary_listener == ["audit"]
    assert await notes(session_factory) == ["audit"]


async def test_commit_failure_after_the_action_calls_its_compensation(
    unit_of_work, transactional, session_factory, monkeypatch
):
    compensated = []

    async def action():
        pass

    async def compensation():
        compensated.append(True)

    with pytest.raises(RuntimeError, match="commit failed"):
        async with unit_of_work() as uow:
            await uow.act(action, compensation=compensation)

            async def failing_commit():
                raise RuntimeError("commit failed")

            monkeypatch.setattr(current_session(), "commit", failing_commit)

    assert compensated == [True]


async def test_current_session_outside_a_unit_of_work_is_an_error():
    with pytest.raises(RuntimeError):
        current_session()


async def test_storage_provides_the_unit_of_work_to_the_core_container():
    builder = ConfigurationBuilder()
    builder.add_values({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    system = await SystemBuilder(builder.applications, builder.build()).abuild()
    try:
        factory = system.provider.get(IUnitOfWorkFactory)
        transactional = system.provider.get(TransactionalEventDispatcher)
        seen = []

        async def listener(event: Noted):
            seen.append((event.note, current_session()))

        transactional.add_listener("test.noted", listener)
        async with factory() as uow:
            await uow.record(Noted("audit"))
        assert [note for note, _ in seen] == ["audit"]
    finally:
        await system.dispose()
