Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- Janitor: ``janitor.period``, ``janitor.old_after`` and ``janitor.enabled`` settings replace the hardcoded sweep period and retention (#339).

Changed
:::::::

- Cache: ``http_cache.storage`` ``ttl`` now expires entries and defaults to ``86400`` (24 hours), ``null`` disables expiry; ``check_ttl_every`` throttles the sweep. They did nothing before (#924).
- Janitor: blobs written in the last 10 minutes are not deleted, and writing already stored content renews them (#1002).
- Pushes to ``main`` publish the ``unstable`` Docker image; version moves to ``0.11.0.dev0``.
- Dashboard Help link opens the ``X.Y`` docs only for final releases, ``latest`` otherwise.
- Docs no longer inject an "unreleased" banner; Read the Docs notifications replace it.

Fixed
:::::

- Janitor: HTTP cache entries are no longer deleted every pass; blobs referenced by a ``cache/meta`` entry are not orphans (#923).
- Metrics: ``storage_blobs_orphans`` no longer counts the blobs the HTTP cache uses (#925).
- Storage: SQL blob storage no longer skips writing a blob another process swept; it asks the database every time (#1002).
- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
