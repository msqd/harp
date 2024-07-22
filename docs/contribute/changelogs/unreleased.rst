Unreleased
==========

Added
:::::

* CLI: it's now possible to load examples from the command line using the ``-e <name>`` flag, and also to load examples
  from an application using ``-e <app:name>``; extension is now detected automatically.
* Rules: examples and documentation
* CLI/Rules: the ``rules`` application now has a command line interface to interact with the rule engine, and allows to
  ``harp rules lint`` and/or ``harp rules run`` a set of rules using a given test request.

Changed
:::::::

* Install(helm): the helm chart now accepts arguments to be passed to the application, and the default values are now
  set in the ``values.yaml`` file.

Fixed
:::::

* CICD: issues with connections checks on certain environments
* Core: server process now corretly uses current working directory as base for relative paths

Updated
:::::::

* bump cryptography from 42.0.8 to 43.0.0
* bump furo from 2024.5.6 to 2024.7.18
* bump hishel from 0.0.29 to 0.0.30
* bump orjson from 3.10.5 to 3.10.6
* bump ruff from 0.4.10 to 0.5.2
* bump sentry-sdk from 2.7.0 to 2.10.0
* bump sphinx from 7.3.7 to 7.4.6
* bump structlog from 24.2.0 to 24.4.0
* bump testcontainers from 4.6.0 to 4.7.2
