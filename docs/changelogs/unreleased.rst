Unreleased
==========

Added
-----

- ApplicationSettingsMixin for standardized enable/disable functionality in application settings
- ``--strict`` CLI flag for enforcing strict configuration validation
- Warning system for misconfigured applications (config exists for unloaded apps)
- Two-pass configuration parsing to filter applications with ``enabled: false``

Changed
-------

- Cookiecutter template migrated from Poetry to UV (PEP 621, Python 3.13, hatchling), with enhanced Makefile, improved prompts, and automatic git initialization.

Fixed
-----

- Generated projects now properly isolate pytest tests and include correct startup instructions.
