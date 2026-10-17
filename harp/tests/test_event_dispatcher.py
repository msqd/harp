import logging

from whistle import Event

from harp.event_dispatcher import LoggingAsyncEventDispatcher


async def test_dispatch_is_logged_at_debug_only(caplog):
    dispatcher = LoggingAsyncEventDispatcher(logger=logging.getLogger("test.dispatcher"))

    with caplog.at_level(logging.INFO, logger="test.dispatcher"):
        await dispatcher.adispatch("foo", Event())

    assert caplog.records == []


async def test_dispatch_is_still_logged_at_debug(caplog):
    dispatcher = LoggingAsyncEventDispatcher(logger=logging.getLogger("test.dispatcher"))

    with caplog.at_level(logging.DEBUG, logger="test.dispatcher"):
        await dispatcher.adispatch("foo", Event())

    assert [r.levelno for r in caplog.records] == [logging.DEBUG]
    assert "[Dispatch] foo" in caplog.records[0].getMessage()
