Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- ``harp create project --harp-source PATH`` (or ``HARP_SOURCE``) scaffolds a project that installs ``harp-proxy`` editable from a local checkout; the cookiecutter integration tests use it (#841).
- Janitor: ``janitor.period``, ``janitor.old_after`` and ``janitor.enabled`` settings replace the hardcoded sweep period and retention (#339).

Changed
:::::::

- Importing ``harp`` no longer configures logging (stdlib ``dictConfig``, ``structlog.configure``) nor disables existing loggers; embedders configure logging themselves. The ``harp`` command still does, with the same formats and ``LOGGING_*`` levels (#944).
- CI documentation and Storybook builds no longer ignore failures and are required by *All Checks Passed*, so they block publishing (#932).
- The CI wheel job no longer sets up Python itself; uv provides the interpreter, as for contributors (#982).
- CI lints Python (``ruff check``, ``ruff format --check``) and the frontend (``pnpm lint``), both required by *All Checks Passed*; ``make lint-frontend`` runs ``pnpm lint``; generated ``src/Models/*.d.ts`` are excluded from ESLint.
- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- Wheel no longer ships stray ``.d.ts`` files: ``vite-plugin-dts`` runs only in the frontend lib build, and ``bin/build_wheel`` fails if the wheel holds one under ``web/`` (#822).
- ``harp create project`` keeps author name, author email and project name verbatim (quotes, backslashes, Jinja, shell characters), and the ``uv tool run`` fallback runs a pinned cookiecutter (#1003).
- Frontend build no longer deletes the tracked ``harp_apps/dashboard/web/.gitkeep``, so a local build leaves the checkout clean (no ``-dirty`` version).
- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).
- Cache: a request reaching the cache transport without an endpoint name now raises a clear error instead of falling into a shared ``__upstream__`` namespace (#913).
- ``harp create project`` floors ``harp-proxy`` at the installed version, ``.dev0`` for pre-releases and dev builds, so a scaffold installs during a pre-release window (#875).
- GitHub release notes no longer start with YAML front matter (#1033).
- ``make wheel`` no longer leaves a wheel in ``dist/`` when its asset check or ``twine check`` fails (#1004).
- Docs: the HTTP cache index warns before the first configuration example that the cache is shared, and what an upstream must send (#873).

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
