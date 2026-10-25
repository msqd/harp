import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "harp_apps/dashboard/frontend/src/Models"
GENERATED = (MODELS_DIR / "Transaction.d.ts", MODELS_DIR / "Schemas/Transaction.json")


@pytest.fixture
def restore_generated_files():
    snapshot = {path: path.read_bytes() for path in GENERATED if path.exists()}
    yield snapshot
    for path, content in snapshot.items():
        path.write_bytes(content)


def test_generate_types_fails_when_json2ts_fails(tmp_path, restore_generated_files):
    failing = tmp_path / "json2ts"
    failing.write_text("#!/bin/sh\nexit 3\n")
    failing.chmod(0o755)

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "generate_types")],
        env={**os.environ, "HARP_JSON2TS": str(failing)},
        capture_output=True,
    )

    assert result.returncode != 0
    types = MODELS_DIR / "Transaction.d.ts"
    assert types.read_bytes() == restore_generated_files[types], "a failing json2ts must not truncate the types"
