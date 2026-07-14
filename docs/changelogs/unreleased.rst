Unreleased
==========

Changed
:::::::

- The published wheel no longer ships test code, snapshots or dev-only testing utilities, reducing the distribution size (the ``harp create project`` scaffolding, which legitimately contains tests, is preserved).

Fixed
:::::

- Replaced the dead GitLab CI/CD pipeline badge and stale "CI/CD" link in the README with the GitHub Actions workflow, aligning the public docs with where CI actually runs since 0.9.0
