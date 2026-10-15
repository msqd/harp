Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

Changed
:::::::

Fixed
:::::

Security
::::::::

* Dashboard user passwords (``dashboard.auth.users.<name>.password``) are masked by ``harp-proxy system config``
  and ``GET /api/system/settings``, whatever the hashing algorithm. ``--unsecure`` still shows them.
* URL passwords are masked when the username is empty (``redis://:password@host``).

Removed
:::::::
