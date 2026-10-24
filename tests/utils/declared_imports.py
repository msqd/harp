"""Find the distributions shipped code imports, to compare with what ``[project.dependencies]`` declares."""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

FIRST_PARTY = {"harp", "harp_apps"}

# The cookiecutter template is the generated project's code, with dependencies of its own.
TEMPLATE_PREFIX = "harp/commandline/cookiecutters/"


def shipped_python_files(repo_root: Path) -> list[Path]:
    """Python files of the wheel, from Hatchling's own selection (so its exclusion list is the only one)."""
    from hatchling.builders.wheel import WheelBuilder

    return sorted(
        repo_root / f.path
        for f in WheelBuilder(str(repo_root)).recurse_included_files()
        if f.path.endswith(".py") and not f.distribution_path.startswith(TEMPLATE_PREFIX)
    )


def declared_distributions(requirements: list[str]) -> set[str]:
    """Normalized distribution names of PEP 508 requirement strings."""
    return {normalize(re.split(r"[\[<>=!~;@ ]", requirement, maxsplit=1)[0]) for requirement in requirements}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def imported_distributions(files: list[Path], import_to_distributions: dict[str, list[str]]) -> dict[str, set[Path]]:
    """Third-party distributions imported by the files, with the files importing them."""
    found = defaultdict(set)
    for file in files:
        for module in _imported_top_level_modules(file):
            if module in FIRST_PARTY or module in sys.stdlib_module_names:
                continue
            for distribution in import_to_distributions.get(module, []):
                found[normalize(distribution)].add(file)
    return dict(found)


def undeclared_imports(
    files: list[Path], declared: set[str], import_to_distributions: dict[str, list[str]]
) -> dict[str, set[Path]]:
    imported = imported_distributions(files, import_to_distributions)
    return {distribution: paths for distribution, paths in imported.items() if distribution not in declared}


def unimported_declarations(
    files: list[Path], declared: set[str], import_to_distributions: dict[str, list[str]]
) -> set[str]:
    """Declared distributions that none of the files imports."""
    return declared - set(imported_distributions(files, import_to_distributions))


def _imported_top_level_modules(file: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(file.read_text())):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules
