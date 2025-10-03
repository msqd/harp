import shlex
import subprocess
import time
from typing import List

from harp import get_logger

logger = get_logger(__name__)


def start_subprocess_with_retry(
    command: List[str], max_retries: int = 3, retry_delay: float = 1.0, startup_check_delay: float = 0.5
) -> subprocess.Popen:
    """Start a subprocess with retry logic.

    Args:
        command: Command to execute.
        max_retries: Maximum number of retry attempts.
        retry_delay: Delay between retries in seconds.
        startup_check_delay: Delay before checking if process started successfully.

    Returns:
        The started subprocess.

    Raises:
        RuntimeError: If subprocess fails to start after max retries.
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting subprocess (attempt {attempt + 1}/{max_retries}): {shlex.join(command)}")
            process = subprocess.Popen(command)

            # Give the process time to start and check if it's still running
            time.sleep(startup_check_delay)
            poll_result = process.poll()
            if poll_result is None:
                logger.info("Subprocess started successfully")
                return process
            else:
                logger.warning(f"Subprocess exited with code {poll_result}")

        except Exception as e:
            logger.error(f"Failed to start subprocess: {e}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    raise RuntimeError(f"Failed to start subprocess after {max_retries} attempts")
