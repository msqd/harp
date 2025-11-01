import asyncio


class CalledProcessError(Exception):
    """Raised when a process returns a non-zero exit code."""

    def __init__(self, returncode, cmd, stdout=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command {cmd} returned non-zero exit status {returncode}")


async def check_output(*args, **kwargs):
    p = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
    stdout_data, stderr_data = await p.communicate()

    if p.returncode != 0:
        raise CalledProcessError(p.returncode, args, stdout_data, stderr_data)

    return stdout_data
