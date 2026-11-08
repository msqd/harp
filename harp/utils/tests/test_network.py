import pytest

from harp.utils.network import wait_for_service_ready


async def test_wait_for_service_ready_waits_between_failed_checks():
    calls = []

    async def not_ready(port):
        calls.append(port)
        return False

    with pytest.raises(TimeoutError):
        await wait_for_service_ready(1, custom_check=not_ready, timeout=0.3, retry_interval=0.1)

    assert len(calls) <= 4
