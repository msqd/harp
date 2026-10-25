import logging
from types import SimpleNamespace

import pytest
from whistle import AsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_STARTED
from harp.asgi.kernel import ASGIKernel
from harp.config.adapters.hypercorn import HypercornAdapter
from harp.utils.network import get_available_network_port


class ConnectionDoesNotExistError(Exception):
    __module__ = "asyncpg.exceptions"


async def _serve_with_failing_startup(error: Exception):
    dispatcher = AsyncEventDispatcher()

    async def fail(event):
        raise error

    dispatcher.add_listener(EVENT_CORE_STARTED, fail)
    system = SimpleNamespace(
        asgi_app=ASGIKernel(dispatcher=dispatcher), binds=[f"localhost:{get_available_network_port()}"]
    )
    await HypercornAdapter(system).serve()


async def test_failing_startup_exits_and_logs_the_error_and_the_postgres_hint(caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exit_info:
        await _serve_with_failing_startup(ConnectionDoesNotExistError("no database"))

    assert exit_info.value.code == -1
    assert "Server initiliation failed" in caplog.text
    assert "no database" in caplog.text
    assert "Could not connect to underlying postgres storage backend" in caplog.text


async def test_other_startup_failures_get_no_postgres_hint(caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit):
        await _serve_with_failing_startup(ValueError("bad config"))

    assert "bad config" in caplog.text
    assert "postgres" not in caplog.text
