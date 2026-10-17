Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

Changed
:::::::

- http_cache: use libyaml (``CSafeLoader``/``CSafeDumper``) to read and write cache entries when available (#1176).
- storage: hash large message bodies off the event loop and without copying the body, blob ids unchanged (#1177).
- event dispatcher: log each dispatch at ``debug`` instead of ``info``.

Fixed
:::::

Security
::::::::

Removed
:::::::
