Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

Changed
:::::::

- Importing ``harp`` no longer configures logging (stdlib ``dictConfig``, ``structlog.configure``) nor disables existing loggers; embedders configure logging themselves. The ``harp`` command still does, with the same formats and ``LOGGING_*`` levels (#944).

Fixed
:::::

Security
::::::::

Removed
:::::::
