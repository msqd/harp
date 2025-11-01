import pytest

from harp.utils.processes import check_output


async def test_check_output_returns_stdout_on_success():
    """Test that check_output returns stdout bytes when command succeeds."""
    result = await check_output("echo", "hello")
    assert result == b"hello\n"


async def test_check_output_raises_on_failure():
    """Test that check_output raises an exception when command fails."""
    with pytest.raises(Exception) as exc_info:
        await check_output("false")
    # Should raise some kind of exception, not return None
    assert exc_info.value is not None
