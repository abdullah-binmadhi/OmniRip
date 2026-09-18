import asyncio

import pytest

from harvester.util.subproc import SubprocessRegistry


@pytest.mark.asyncio
async def test_registry_terminates_process_by_job_prefix() -> None:
    registry = SubprocessRegistry()
    process = await asyncio.create_subprocess_exec(
        "python",
        "-c",
        "import time; time.sleep(30)",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await registry.register("job:yt-dlp:1", process)
    await registry.terminate_prefix("job", grace_s=0.1)

    assert process.returncode is not None
    assert await registry.keys() == ()
