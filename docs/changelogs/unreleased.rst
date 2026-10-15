Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- Janitor: ``janitor.period``, ``janitor.old_after`` and ``janitor.enabled`` settings replace the hardcoded sweep period and retention (#339).

Changed
:::::::

- CI documentation and Storybook builds no longer ignore failures and are required by *All Checks Passed*, so they block publishing (#932).
- The CI wheel job no longer sets up Python itself; uv provides the interpreter, as for contributors (#982).
- CI lints Python (``ruff check``, ``ruff format --check``) and the frontend (``pnpm lint``), both required by *All Checks Passed*; ``make lint-frontend`` runs ``pnpm lint``; generated ``src/Models/*.d.ts`` are excluded from ESLint.
- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).
- GitHub release notes no longer start with YAML front matter (#1033).
- ``make wheel`` no longer leaves a wheel in ``dist/`` when its asset check or ``twine check`` fails (#1004).

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
