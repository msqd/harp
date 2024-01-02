import asyncio


async def check_output(*args, **kwargs):
    p = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
    stdout_data, stderr_data = await p.communicate()

    if p.returncode == 0:
        return stdout_data
