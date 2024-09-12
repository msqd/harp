Unreleased
==========

Added
:::::

- Core/Services: Ability to include another services.yml file, either by absolute path (using
  "!include /path/to/other.yml") or from a python package path, using "!include services.yml from my.package" syntax.
- Core/Logging: The root logging level is now configurable using LOGGING=...
