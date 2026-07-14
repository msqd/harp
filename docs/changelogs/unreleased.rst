Unreleased
==========

Fixed
:::::

- Replaced the dead GitLab CI/CD pipeline badge and stale "CI/CD" link in the README with the GitHub Actions workflow, aligning the public docs with where CI actually runs since 0.9.0
- Restored the ``harp`` command as an alias of ``harp-proxy`` so ``harp ...`` and ``uv run harp ...`` run the CLI instead of executing the package directory (which shadowed the stdlib ``typing`` module and crashed from a source checkout); the documented ``harp create project`` flow now works.
