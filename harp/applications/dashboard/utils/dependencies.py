import sys

from harp.utils.processes import check_output


def parse_dependencies(dependencies: list[str]) -> dict[str, str]:
    """Transform a list of dependencies into a dictionary of dependencies, with package name as key."""
    parsed = {}

    for dependency in dependencies:
        if dependency.startswith("-e"):
            pkg_repo, pkg_name = dependency.rsplit("/", 1)
            if pkg_name in parsed:
                raise ValueError(f"Duplicate package name {pkg_name} in dependencies.")
            parsed[pkg_name] = pkg_repo + "/" + pkg_name
        else:
            pkg_name, pkg_version = dependency.split("==")
            if pkg_name in parsed:
                raise ValueError(f"Duplicate package name {pkg_name} in dependencies.")
            parsed[pkg_name] = pkg_version
    return parsed


async def get_python_dependencies():
    return list(
        filter(
            lambda x: x and not x.startswith("#"),
            (await check_output(sys.executable, "-m", "pip", "freeze")).decode("utf-8").split("\n"),
        ),
    )
