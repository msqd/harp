import sys

from harp.utils.processes import check_output


def parse_dependencies(dependencies: list[str]) -> dict[str, str]:
    """Transform a list of dependencies into a dictionary of dependencies, with package name as key."""
    parsed = {}

    for dependency in dependencies:
        # Skip empty lines or comments
        if not dependency or dependency.startswith("#"):
            continue

        # Handle editable packages
        if dependency.startswith("-e"):
            pkg_repo, pkg_name = dependency.rsplit("/", 1)
            pkg_name = pkg_name.split("#egg=")[-1]  # Extract package name
            pkg_version = "editable"
        else:
            parts = dependency.split("==")
            if len(parts) == 2:
                pkg_name, pkg_version = parts
            else:
                # Handle packages without a version or with unusual formatting
                pkg_name, pkg_version = parts[0], "unknown"

        # Check for duplicates
        if pkg_name in parsed:
            raise ValueError(f"Duplicate package name {pkg_name} found.")
        parsed[pkg_name] = pkg_version
    return parsed


async def get_python_dependencies():
    return list(
        filter(
            lambda x: x and not x.startswith("#"),
            (await check_output(sys.executable, "-m", "pip", "freeze")).decode("utf-8").split("\n"),
        ),
    )
