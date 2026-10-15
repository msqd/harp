Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- Janitor: ``janitor.period``, ``janitor.old_after`` and ``janitor.enabled`` settings replace the hardcoded sweep period and retention (#339).

Changed
:::::::

- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- Dashboard: unknown URLs and unknown transactions show a "not found" page inside the layout instead of a crash screen or an empty card, and the "copy transaction link" button yields ``/transactions/<id>`` from the detail page (#877).
- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
