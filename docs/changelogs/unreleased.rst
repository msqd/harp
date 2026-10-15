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

- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- ``harp create project`` keeps author name, author email and project name verbatim (quotes, backslashes, Jinja, shell characters), and the ``uv tool run`` fallback runs a pinned cookiecutter (#1003).
- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).
- ``harp create project`` floors ``harp-proxy`` at the installed version, ``.dev0`` for pre-releases and dev builds, so a scaffold installs during a pre-release window (#875).

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
