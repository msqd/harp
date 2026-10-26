"""The janitor schedules sweeps and knows no application."""

import ast
from pathlib import Path

import harp_apps.janitor

JANITOR = Path(harp_apps.janitor.__file__).parent


def imported_modules(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            modules.add(("." * node.level) + (node.module or ""))
    return modules


def test_the_janitor_imports_no_other_application():
    sources = [p for p in JANITOR.rglob("*.py") if "tests" not in p.parts]
    assert sources

    offenders = {
        p.name: module
        for p in sources
        for module in imported_modules(p)
        if module.startswith(("harp_apps", "..")) and not module.startswith("harp_apps.janitor")
    }

    assert offenders == {}
