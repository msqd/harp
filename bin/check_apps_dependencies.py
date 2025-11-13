#!/usr/bin/env python3
"""
Check application dependencies against actual imports.

This script analyzes all HARP applications and compares their declared
dependencies with actual imports found in the code. It helps maintain
accurate dependency declarations.

Usage:
    python bin/check_apps_dependencies.py
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class DependencyAnalysis(NamedTuple):
    """Analysis results for an application."""

    app_name: str
    declared_deps: set[str]
    actual_imports: set[str]
    undeclared: set[str]  # Imports not in declared deps
    potentially_unused: set[str]  # Declared but never imported


def find_harp_apps() -> list[Path]:
    """Find all application directories in harp_apps/."""
    harp_apps_dir = Path(__file__).parent.parent / "harp_apps"
    return [
        d for d in harp_apps_dir.iterdir() if d.is_dir() and not d.name.startswith("_") and (d / "__app__.py").exists()
    ]


def extract_declared_dependencies(app_dir: Path) -> set[str]:
    """Extract declared dependencies from __app__.py."""
    app_file = app_dir / "__app__.py"
    if not app_file.exists():
        return set()

    try:
        tree = ast.parse(app_file.read_text())
        for node in ast.walk(tree):
            # Look for: application = Application(dependencies=[...])
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "application":
                        if isinstance(node.value, ast.Call):
                            # Find dependencies keyword argument
                            for keyword in node.value.keywords:
                                if keyword.arg == "dependencies":
                                    if isinstance(keyword.value, ast.List):
                                        deps = set()
                                        for elt in keyword.value.elts:
                                            if isinstance(elt, ast.Constant):
                                                deps.add(elt.value)
                                        return deps
    except SyntaxError:
        pass

    return set()


def extract_harp_imports(file_path: Path) -> set[str]:
    """Extract harp_apps imports from a Python file."""
    imports = set()

    try:
        tree = ast.parse(file_path.read_text())

        for node in ast.walk(tree):
            # Handle: from harp_apps.xxx import ...
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("harp_apps."):
                    parts = node.module.split(".")
                    if len(parts) >= 2:
                        app_name = parts[1]
                        # Skip contrib submodules
                        if app_name != "contrib":
                            imports.add(app_name)

            # Handle: import harp_apps.xxx
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("harp_apps."):
                        parts = alias.name.split(".")
                        if len(parts) >= 2:
                            app_name = parts[1]
                            if app_name != "contrib":
                                imports.add(app_name)

    except SyntaxError:
        pass

    return imports


def scan_app_imports(app_dir: Path) -> set[str]:
    """Scan all Python files in an app directory for harp_apps imports."""
    all_imports = set()

    for py_file in app_dir.rglob("*.py"):
        # Skip test files
        if "test" in py_file.parts or py_file.name.startswith("test_"):
            continue

        # Skip __pycache__
        if "__pycache__" in py_file.parts:
            continue

        imports = extract_harp_imports(py_file)
        all_imports.update(imports)

    # Remove self-references
    app_name = app_dir.name
    all_imports.discard(app_name)

    return all_imports


def analyze_app(app_dir: Path) -> DependencyAnalysis:
    """Analyze a single application's dependencies."""
    app_name = app_dir.name
    declared_deps = extract_declared_dependencies(app_dir)
    actual_imports = scan_app_imports(app_dir)

    undeclared = actual_imports - declared_deps
    potentially_unused = declared_deps - actual_imports

    return DependencyAnalysis(
        app_name=app_name,
        declared_deps=declared_deps,
        actual_imports=actual_imports,
        undeclared=undeclared,
        potentially_unused=potentially_unused,
    )


def print_report(analyses: list[DependencyAnalysis]) -> None:
    """Print a formatted report of dependency analysis."""
    print("=" * 80)
    print("HARP Application Dependency Analysis")
    print("=" * 80)
    print()

    # Group by issue type
    apps_with_undeclared = []
    apps_with_unused = []
    apps_perfect = []

    for analysis in sorted(analyses, key=lambda a: a.app_name):
        if analysis.undeclared or analysis.potentially_unused:
            if analysis.undeclared:
                apps_with_undeclared.append(analysis)
            if analysis.potentially_unused:
                apps_with_unused.append(analysis)
        else:
            apps_perfect.append(analysis)

    # Report apps with undeclared dependencies
    if apps_with_undeclared:
        print("⚠️  UNDECLARED DEPENDENCIES")
        print("-" * 80)
        for analysis in apps_with_undeclared:
            print(f"\n{analysis.app_name}:")
            print(f"  Declared: {sorted(analysis.declared_deps) or 'none'}")
            print(f"  Imports:  {sorted(analysis.actual_imports) or 'none'}")
            print(f"  ⚠️  Missing in dependencies: {sorted(analysis.undeclared)}")
        print()

    # Report apps with potentially unused dependencies
    if apps_with_unused:
        print("ℹ️  POTENTIALLY UNUSED DEPENDENCIES")
        print("-" * 80)
        print("(These may be runtime dependencies or optional imports)")
        for analysis in apps_with_unused:
            print(f"\n{analysis.app_name}:")
            print(f"  Declared: {sorted(analysis.declared_deps)}")
            print(f"  Imports:  {sorted(analysis.actual_imports) or 'none'}")
            print(f"  ℹ️  Not imported: {sorted(analysis.potentially_unused)}")
        print()

    # Report apps with correct dependencies
    if apps_perfect:
        print("✅ CORRECT DEPENDENCIES")
        print("-" * 80)
        for analysis in apps_perfect:
            deps_str = ", ".join(sorted(analysis.declared_deps)) if analysis.declared_deps else "none"
            print(f"  {analysis.app_name}: {deps_str}")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total applications analyzed: {len(analyses)}")
    print(f"  ✅ Correct dependencies:        {len(apps_perfect)}")
    print(f"  ⚠️  Undeclared dependencies:     {len(apps_with_undeclared)}")
    print(f"  ℹ️  Potentially unused:          {len(apps_with_unused)}")
    print()

    if apps_with_undeclared:
        print("⚠️  Action required: Add missing dependencies to __app__.py")
        return 1
    elif apps_with_unused:
        print("ℹ️  Review recommended: Check if unused dependencies are needed")
        return 0
    else:
        print("✅ All dependencies are correctly declared!")
        return 0


def main() -> int:
    """Main entry point."""
    print("Scanning HARP applications for dependency issues...\n")

    app_dirs = find_harp_apps()
    if not app_dirs:
        print("Error: No HARP applications found in harp_apps/")
        return 1

    analyses = [analyze_app(app_dir) for app_dir in app_dirs]
    return print_report(analyses)


if __name__ == "__main__":
    sys.exit(main())
