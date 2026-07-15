Unreleased
==========

Changed
:::::::

- **BC break:** renamed the ``harp.typing`` package to ``harp.typedefs`` so a first-party module no longer shadows the standard-library ``typing`` module (which crashed the CLI when the ``harp/`` directory ended up on ``sys.path``). Update imports from ``harp.typing`` to ``harp.typedefs``.
- The published wheel no longer ships test code, snapshots or dev-only testing utilities, reducing the distribution size (the ``harp create project`` scaffolding, which legitimately contains tests, is preserved).

Fixed
:::::

- Replaced the dead GitLab CI/CD pipeline badge and stale "CI/CD" link in the README with the GitHub Actions workflow, aligning the public docs with where CI actually runs since 0.9.0
- Restored the ``harp`` command as an alias of ``harp-proxy`` so ``harp ...`` and ``uv run harp ...`` run the CLI instead of executing the package directory (which shadowed the stdlib ``typing`` module and crashed from a source checkout); the documented ``harp create project`` flow now works.
