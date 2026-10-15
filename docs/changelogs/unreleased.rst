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

- Cache: a stored response with no ``Date`` header now gets one set to its time of receipt, so its ``max-age`` expires instead of serving fresh forever (#963).

Security
::::::::

Removed
:::::::
