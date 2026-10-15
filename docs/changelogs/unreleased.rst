Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

Changed
:::::::

- CI lints Python (``ruff check``, ``ruff format --check``) and the frontend (``pnpm lint``), both required by *All Checks Passed*; ``make lint-frontend`` runs ``pnpm lint``; generated ``src/Models/*.d.ts`` are excluded from ESLint.
- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).

Security
::::::::

Removed
:::::::
