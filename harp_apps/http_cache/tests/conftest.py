"""Test fixtures for http_cache tests."""

import sys
from pathlib import Path

# Add root directory to path to allow importing from tests
root_dir = Path(__file__).parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import test_api fixture from tests.conftest
from tests.conftest import test_api, StubServerDescription  # noqa: F401, E402
