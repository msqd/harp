Configuration
=============

.. warning::

    For now, please **only use environment variables or the python API for configuration**.

    YAML, JSON, TOML, INI files should be supported in the future but are not a priority at the moment.

Basics
::::::

Configuration is built from different sources that may override each other. From lowest to hightest priority (lower items will override items configured by a higher item):

- default settings (provided by harp or harp extensions)
- python proxy factory settings (passed to :class:`ProxyFactory <harp.core.factories.proxy.ProxyFactory>`)
- configuration files (YAML, JSON, TOML, INI, ...) in order of appearance (first file will be overridden by second file, etc.)
- environment variables
- command line arguments

.. warning::

    The described logic is a targert, but is not yet fully implemented.


.. toctree::
    :maxdepth: 2

    endpoints
    logging
    storage
