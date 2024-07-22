Configuration
=============

Configuration is built from different sources that may override each other. From lowest to hightest priority (lower items will override items configured by a higher item):

- default settings (provided by harp or harp extensions)
- proxy factory settings (python)
- configuration files (YAML, JSON, TOML, INI, ...) in order of appearance (first file will be overridden by second file, etc.)
- environment variables
- command line arguments

.. warning::

    This section is a work in progress.

Table of Content
::::::::::::::::

* :doc:`Dashboard </apps/dashboard/index>`: web interface
* :doc:`Http Client </apps/http_client/index>`: timeouts, cache, ...
* :doc:`Janitor </apps/janitor/index>`: housekeeping
* :doc:`Proxy & Endpoints </apps/proxy/index>`: endpoints, names, ports, ...
* :doc:`Storage </apps/storage/index>`: relational and non-relational storages
* :doc:`Telemetry </apps/telemetry/index>`: usage reporting
* :doc:`Rules Engine </apps/rules/index>`: fine tuning request lifecycle
