import logging
from contextlib import asynccontextmanager

import pytest
from whistle import AsyncEventDispatcher, Event

from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.unit_of_work import (
    TransactionalEventDispatcher,
    UnitOfWork,
    UnsupportedEventError,
    auditable,
    is_auditable,
    is_loggable,
    loggable,
)


@auditable("test.audited")
class Audited(Event):
    pass


@loggable("test.logged")
class Logged(Event):
    pass


class Unmarked(Event):
    pass


class FakeUnitOfWork(UnitOfWork):
    """Records what its transaction does, without any persistence."""

    def __init__(self, *args, fail_commit: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.journal: list[str] = []
        self.fail_commit = fail_commit

    @asynccontextmanager
    async def _transaction(self):
        self.journal.append("begin")
        try:
            yield
        except BaseException:
            self.journal.append("rollback")
            raise
        if self.fail_commit:
            self.journal.append("commit failed")
            raise RuntimeError("commit failed")
        self.journal.append("commit")


@pytest.fixture
def transactional():
    return TransactionalEventDispatcher()


@pytest.fixture
def dispatcher():
    return LoggingAsyncEventDispatcher()


@pytest.fixture
def make_uow(transactional, dispatcher):
    def make(**kwargs):
        return FakeUnitOfWork(transactional=transactional, dispatcher=dispatcher, **kwargs)

    return make


def test_marks():
    assert is_auditable(Audited()) and not is_loggable(Audited())
    assert is_loggable(Logged()) and not is_auditable(Logged())
    assert not is_auditable(Unmarked()) and not is_loggable(Unmarked())


def test_transactional_dispatcher_is_an_async_dispatcher_with_its_own_listeners():
    first, second = TransactionalEventDispatcher(), TransactionalEventDispatcher()
    assert isinstance(first, AsyncEventDispatcher)

    async def listener(event):
        pass

    first.add_listener("test.audited", listener)
    assert second.get_listeners("test.audited") == ()


async def test_record_refuses_an_unmarked_event(make_uow):
    uow = make_uow()
    with pytest.raises(UnsupportedEventError):
        async with uow:
            await uow.record(Unmarked())
    assert uow.journal == ["begin", "rollback"]


async def test_record_refuses_a_loggable_event(make_uow):
    with pytest.raises(UnsupportedEventError):
        async with make_uow() as uow:
            await uow.record(Logged())


async def test_transactional_listener_runs_inside_the_transaction(make_uow, transactional):
    uow = make_uow()

    async def listener(event):
        uow.journal.append("transactional listener")

    transactional.add_listener("test.audited", listener)

    async with uow:
        await uow.record(Audited())

    assert uow.journal == ["begin", "transactional listener", "commit"]


async def test_ordinary_listener_runs_after_the_commit_only(make_uow, dispatcher):
    uow = make_uow()

    async def listener(event):
        uow.journal.append("ordinary listener")

    dispatcher.add_listener("test.audited", listener)

    async with uow:
        await uow.record(Audited())
        assert uow.journal == ["begin"]

    assert uow.journal == ["begin", "commit", "ordinary listener"]


async def test_transactional_listener_never_runs_on_main_dispatcher_and_vice_versa(make_uow, transactional, dispatcher):
    uow = make_uow()
    seen = []

    async def only_transactional(event):
        seen.append("t")

    async def only_main(event):
        seen.append("m")

    transactional.add_listener("test.audited", only_transactional)
    dispatcher.add_listener("test.audited", only_main)

    async with uow:
        await uow.record(Audited())

    assert seen == ["t", "m"]


async def test_transactional_listener_failure_rolls_back_and_fails_the_action(make_uow, transactional, dispatcher):
    uow = make_uow()
    after = []

    async def failing(event):
        raise ValueError("audit write failed")

    async def ordinary(event):
        after.append(event)

    transactional.add_listener("test.audited", failing)
    dispatcher.add_listener("test.audited", ordinary)

    with pytest.raises(ValueError, match="audit write failed"):
        async with uow:
            await uow.record(Audited())

    assert uow.journal == ["begin", "rollback"]
    assert after == []


async def test_main_listener_failure_is_logged_and_the_commit_stands(make_uow, dispatcher, caplog):
    uow = make_uow()
    later = []

    async def failing(event):
        raise ValueError("webhook down")

    async def other(event):
        later.append(event)

    dispatcher.add_listener("test.audited", failing)
    dispatcher.add_listener("test.audited", other, priority=-1)

    with caplog.at_level(logging.ERROR):
        async with uow:
            await uow.record(Audited())

    assert uow.journal == ["begin", "commit"]
    assert any("webhook down" in r.getMessage() or "webhook down" in str(r.exc_info) for r in caplog.records)


async def test_nothing_is_dispatched_after_when_the_body_fails(make_uow, dispatcher):
    uow = make_uow()
    after = []

    async def ordinary(event):
        after.append(event)

    dispatcher.add_listener("test.audited", ordinary)

    with pytest.raises(RuntimeError):
        async with uow:
            await uow.record(Audited())
            raise RuntimeError("boom")

    assert uow.journal == ["begin", "rollback"]
    assert after == []


async def test_nothing_is_dispatched_after_when_the_commit_fails(make_uow, dispatcher):
    uow = make_uow(fail_commit=True)
    after = []

    async def ordinary(event):
        after.append(event)

    dispatcher.add_listener("test.audited", ordinary)

    with pytest.raises(RuntimeError, match="commit failed"):
        async with uow:
            await uow.record(Audited())

    assert after == []


async def test_act_runs_between_the_write_and_the_commit(make_uow):
    uow = make_uow()

    async def action():
        uow.journal.append("action")

    async with uow:
        await uow.record(Audited())
        await uow.act(action)

    assert uow.journal == ["begin", "action", "commit"]


async def test_failing_action_leaves_nothing(make_uow, dispatcher):
    uow = make_uow()
    after = []

    async def ordinary(event):
        after.append(event)

    dispatcher.add_listener("test.audited", ordinary)

    async def action():
        raise RuntimeError("action failed")

    compensated = []

    async def compensation():
        compensated.append(True)

    with pytest.raises(RuntimeError, match="action failed"):
        async with uow:
            await uow.record(Audited())
            await uow.act(action, compensation=compensation)

    assert uow.journal == ["begin", "rollback"]
    assert after == []
    assert compensated == []


async def test_commit_failure_after_the_action_calls_its_compensation(make_uow):
    uow = make_uow(fail_commit=True)
    compensated = []

    async def action():
        pass

    async def compensation():
        compensated.append(True)

    with pytest.raises(RuntimeError, match="commit failed"):
        async with uow:
            await uow.act(action, compensation=compensation)

    assert compensated == [True]


async def test_commit_failure_after_an_action_without_compensation_logs_critical(make_uow, caplog):
    uow = make_uow(fail_commit=True)

    async def action():
        pass

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(RuntimeError, match="commit failed"):
            async with uow:
                await uow.act(action)

    assert [r.levelno for r in caplog.records] == [logging.CRITICAL]


async def test_commit_failure_without_action_logs_no_critical(make_uow, caplog):
    uow = make_uow(fail_commit=True)

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(RuntimeError, match="commit failed"):
            async with uow:
                await uow.record(Audited())

    assert caplog.records == []


async def test_compensations_run_in_reverse_order(make_uow):
    uow = make_uow(fail_commit=True)
    order = []

    async def noop():
        pass

    def compensation(name):
        async def run():
            order.append(name)

        return run

    with pytest.raises(RuntimeError):
        async with uow:
            await uow.act(noop, compensation=compensation("first"))
            await uow.act(noop, compensation=compensation("second"))

    assert order == ["second", "first"]


async def test_core_container_provides_a_transactional_dispatcher_distinct_from_the_main_one():
    from harp.config import ApplicationsRegistry
    from harp.config.builders.system import SystemBuilder
    from harp.typedefs import GlobalSettings

    system = await SystemBuilder(ApplicationsRegistry(), GlobalSettings(applications={})).abuild()
    try:
        transactional = system.provider.get(TransactionalEventDispatcher)
        assert isinstance(transactional, TransactionalEventDispatcher)
        assert transactional is not system.dispatcher
        assert system.provider.get(TransactionalEventDispatcher) is transactional
    finally:
        await system.dispose()
