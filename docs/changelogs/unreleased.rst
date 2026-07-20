Unreleased
==========

Added
:::::

- ``harp create project`` now accepts the project name as an argument and ``--no-app`` / ``--no-config`` flags to skip the application folder or the config file, running without interactive prompts when the name and git author (from ``git config``) are available. New projects are created with an application folder by default.

Changed
:::::::

- **BC break:** renamed the ``harp.typing`` package to ``harp.typedefs`` so a first-party module no longer shadows the standard-library ``typing`` module (which crashed the CLI when the ``harp/`` directory ended up on ``sys.path``). Update imports from ``harp.typing`` to ``harp.typedefs``.
- The published wheel no longer ships test code, snapshots or dev-only testing utilities, reducing the distribution size (the ``harp create project`` scaffolding, which legitimately contains tests, is preserved).
- ``harp create`` now runs cookiecutter as a subprocess, falling back to ``uv tool run cookiecutter`` when it is not installed as a package, and its guidance no longer mentions Poetry (completes the UV migration for the project bootstrap tooling).

Fixed
:::::

- Replaced the dead GitLab CI/CD pipeline badge and stale "CI/CD" link in the README with the GitHub Actions workflow, aligning the public docs with where CI actually runs since 0.9.0
- Restored the ``harp`` command as an alias of ``harp-proxy`` so ``harp ...`` and ``uv run harp ...`` run the CLI instead of executing the package directory (which shadowed the stdlib ``typing`` module and crashed from a source checkout); the documented ``harp create project`` flow now works.
- Committed a ``.gitkeep`` in ``harp_apps/dashboard/web/`` so a fresh clone can ``uv sync`` and build the wheel; the directory is a hatchling force-include target and previously vanished on checkout (its ``.gitignore`` allow-rule was overridden by a later pattern), making the build fail with ``FileNotFoundError``.
