"""Keep the release image installable, pinned and lean."""

import re
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text()
FROM_LINES = re.findall(r"^FROM (\S+)", DOCKERFILE, re.MULTILINE)


def test_single_dockerfile():
    assert not (ROOT / "Dockerfile.pypi").exists()


def test_default_docker_python_matches_project_requirement():
    requirement = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]
    for image in FROM_LINES:
        match = re.match(r"python:(\d+\.\d+)-slim@", image)
        assert match is not None, f"{image} must be a python slim image"
        assert match.group(1) in SpecifierSet(requirement), f"{image} is outside requires-python {requirement}"


def test_base_images_are_pinned_by_digest():
    assert FROM_LINES
    for image in FROM_LINES:
        assert re.search(r"@sha256:[0-9a-f]{64}$", image), f"{image} is not pinned by digest"


def test_runtime_image_has_no_pip():
    runtime = DOCKERFILE.split("\nFROM ")[-1]
    assert "pip uninstall" in runtime
    assert "pip install" not in runtime


def test_healthcheck_fetches_healthz():
    assert re.search(r"^HEALTHCHECK .*\n?.*/healthz", DOCKERFILE, re.MULTILINE)
