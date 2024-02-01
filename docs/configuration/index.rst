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

.. toctree::
    :maxdepth: 2

    Dashboard <../apps/dashboard/index>
    Proxy <../apps/proxy/index>
    logging
    storage
