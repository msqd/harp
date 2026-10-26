"""The image ships what ``uv.lock`` pins: the comparison behind ``bin/check_docker_lock`` and the Dockerfile wiring."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("check_docker_lock", ROOT / "bin" / "check_docker_lock.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

LOCK = """\
aiofiles==25.1.0
Typing_Extensions==4.15.0
colorama==0.4.6 ; sys_platform == 'win32'
cffi==2.0.0 ; platform_python_implementation != 'PyPy'
"""


def test_lock_names_are_normalized_and_foreign_markers_skipped():
    assert check.parse_requirements(LOCK) == {
        "aiofiles": "25.1.0",
        "typing-extensions": "4.15.0",
        "cffi": "2.0.0",
    }


def test_matching_image_has_no_difference():
    installed = "aiofiles==25.1.0\ntyping_extensions==4.15.0\ncffi==2.0.0\nharp-proxy==0.13.0\n"
    assert check.differences(check.parse_requirements(LOCK), check.parse_requirements(installed)) == []


def test_version_drift_is_reported():
    installed = "aiofiles==25.2.0\ntyping_extensions==4.15.0\ncffi==2.0.0\n"
    assert check.differences(check.parse_requirements(LOCK), check.parse_requirements(installed)) == [
        "aiofiles: lock 25.1.0, image 25.2.0"
    ]


def test_missing_and_unlocked_packages_are_reported():
    installed = "aiofiles==25.1.0\ntyping_extensions==4.15.0\nrequests==2.0\n"
    assert check.differences(check.parse_requirements(LOCK), check.parse_requirements(installed)) == [
        "cffi: lock 2.0.0, image missing",
        "requests: not in lock, image 2.0",
    ]


def test_dockerfile_installs_the_wheel_constrained_to_the_lock():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert re.search(r"pip install .*-c \S*constraints\.txt", dockerfile)


def test_dockerfile_installs_the_extras_the_lock_is_exported_with():
    dockerfile = (ROOT / "Dockerfile").read_text()
    extras = re.search(r"harp-proxy\[([^\]]+)\]", dockerfile).group(1).split(",")
    assert tuple(extras) == check.EXTRAS


def test_image_supports_argon2_dashboard_hashes():
    assert "argon2" in check.EXTRAS
