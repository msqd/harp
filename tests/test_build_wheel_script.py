"""``bin/build_wheel`` must not publish a wheel into ``dist/`` before it has passed its checks.

The script runs against stubbed ``make``, ``uv`` and ``uvx`` executables, so no network and no frontend build are
needed: the stubs only decide how many dashboard assets the wheel holds and whether ``twine check`` passes.
"""

import os
import subprocess
import sys
from pathlib import Path


BUILD_WHEEL = Path(__file__).resolve().parent.parent / "bin" / "build_wheel"

MAKE_STUB = """#!/bin/bash
mkdir -p harp_apps/dashboard/frontend harp_apps/dashboard/web
touch harp_apps/dashboard/web/index.html
"""

UV_STUB = f"""#!/bin/bash
if [ "$1" = "build" ]; then
    mkdir -p dist
    "{sys.executable}" -c 'import os, zipfile
with zipfile.ZipFile("dist/harp-0.whl", "w") as z:
    for i in range(int(os.environ["WEB_ASSETS"])):
        z.writestr("harp_apps/dashboard/web/asset%d" % i, "")'
else
    shift 3  # run --no-project python
    exec "{sys.executable}" "$@"
fi
"""

UVX_STUB = """#!/bin/bash
exit "$TWINE_EXIT"
"""


def _run_build_wheel(tmp_path: Path, *, web_assets: int, twine_exit: int):
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, content in (("make", MAKE_STUB), ("uv", UV_STUB), ("uvx", UVX_STUB)):
        (stubs / name).write_text(content)
        (stubs / name).chmod(0o755)

    work, original = tmp_path / "work", tmp_path / "original"
    (original / "dist").mkdir(parents=True)
    work.mkdir()
    (work / "README.rst").write_text("Harp\n\nPeople & Credits\n")

    result = subprocess.run(
        ["bash", str(BUILD_WHEEL)],
        cwd=work,
        capture_output=True,
        env={
            **os.environ,
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "PWD_ORIG": str(original),
            "UV": "uv",
            "UVX": "uvx",
            "WEB_ASSETS": str(web_assets),
            "TWINE_EXIT": str(twine_exit),
        },
    )
    return result, sorted(p.name for p in (original / "dist").iterdir())


def test_wheel_passing_both_checks_lands_in_dist(tmp_path):
    result, dist = _run_build_wheel(tmp_path, web_assets=10, twine_exit=0)

    assert result.returncode == 0
    assert dist == ["harp-0.whl"]


def test_wheel_failing_asset_guard_leaves_dist_untouched(tmp_path):
    result, dist = _run_build_wheel(tmp_path, web_assets=9, twine_exit=0)

    assert result.returncode != 0
    assert dist == []


def test_wheel_failing_twine_check_leaves_dist_untouched(tmp_path):
    result, dist = _run_build_wheel(tmp_path, web_assets=10, twine_exit=1)

    assert result.returncode != 0
    assert dist == []
