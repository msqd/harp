"""
Regenerate the images used by the README and the docs.

    uv run python -m docs._captures [captures|diagrams]

``captures``: a throwaway SQLite database is created and filled with the fixed data of :mod:`docs._captures.seed`, a
real HARP serves the real dashboard on it with a frozen clock, and Playwright (the one of the dashboard frontend) takes
the screenshots, into ``docs/user/images``.

``diagrams``: renders each ``docs/images/diagrams/*.dot`` to an SVG next to it, for the README, which cannot run Sphinx.
The docs render the same ``.dot`` sources themselves at build time.
"""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from docs._captures.seed import seed

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "docs/images/diagrams"

# Fixed, not picked at random: the settings page of the dashboard shows them, and a capture must not change between runs.
DASHBOARD_PORT = 49701
ENDPOINTS = {"payments": 49711, "geocoding": 49712, "weather": 49713}
CONFIG = """\
storage:
  url: sqlite+aiosqlite:///harp.db
dashboard:
  port: {dashboard_port}
  auth:
    type: none
proxy:
  endpoints:
{endpoints}
"""
ENDPOINT = """\
    - name: {name}
      port: {port}
      remote:
        endpoints:
          - url: https://{name}.example.com
"""


def write_config(directory: Path) -> Path:
    endpoints = "".join(ENDPOINT.format(name=name, port=port) for name, port in ENDPOINTS.items())
    path = directory / "harp.yml"
    path.write_text(CONFIG.format(dashboard_port=DASHBOARD_PORT, endpoints=endpoints.rstrip("\n")))
    return path


def wait_until_up(url: str, timeout: float = 60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urlopen(url, timeout=2).close()
            return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"{url} did not come up")


def render_diagrams(directory: Path = DIAGRAMS):
    for source in sorted(directory.glob("*.dot")):
        subprocess.run(["dot", "-Tsvg", str(source), "-o", str(source.with_suffix(".svg"))], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("what", nargs="?", choices=["captures", "diagrams"], help="all of them when omitted")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/user/images", help="where the PNG captures go")
    args = parser.parse_args()

    if args.what in (None, "diagrams"):
        render_diagrams()
    if args.what in (None, "captures"):
        capture(args.output)


def capture(output: Path):
    # PYTHONHASHSEED: the dashboard lists facet values in set order, which follows string hashes.
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONHASHSEED": "0"}
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        config = write_config(directory)

        # The database is relative to the working directory, so the storage page does not show where the temp dir is.
        subprocess.run(
            [sys.executable, "-m", "harp", "db:migrate", "up", "head", "-f", str(config)],
            check=True,
            env=env,
            cwd=directory,
        )
        asyncio.run(seed(f"sqlite+aiosqlite:///{directory / 'harp.db'}"))

        server = subprocess.Popen(
            [sys.executable, "-m", "docs._captures.serve", "server", "-f", str(config)],
            env=env,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            wait_until_up(f"http://localhost:{DASHBOARD_PORT}/api/system")
            output.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "node",
                    str(Path(__file__).with_name("capture.mjs")),
                    f"http://localhost:{DASHBOARD_PORT}",
                    str(output),
                ],
                check=True,
            )
        finally:
            os.killpg(server.pid, signal.SIGTERM)
            server.wait(timeout=30)


if __name__ == "__main__":
    main()
