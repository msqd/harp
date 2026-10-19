Getting Started
===============

This guide contains everything you need to download, install, and run HARP Proxy.

.. toctree::
    :maxdepth: 2

    quick


System Requirements
:::::::::::::::::::

HARP Proxy has minimal system requirements:

- **Python**: 3.13+ (automatically managed by UV)
- **Ports**: 4080 for the dashboard by default; proxy endpoints listen on the ports you configure (no endpoint exists by default)
- **Memory**: ~50MB base, scales with traffic and cache size. If recording falls behind the database, queued request and response bodies add up to about 1,250 × (request body + response body), 2.5 GiB at the 1 MiB body cap (see :ref:`storage-memory-sizing`)
- **Storage**: Depends on database backend (SQLite in-memory by default)

For production deployments, use PostgreSQL for persistent storage. SQLite is for development only and MySQL/MariaDB is deprecated.


Installation
::::::::::::

Several options exist to install HARP Proxy on your development machine.

The **recommended** method is :doc:`using UV <uv>`, a fast Python package manager that makes installation and execution simple.

For containerized environments, you can use :doc:`Docker containers <docker>`, ensuring you have the exact set of
dependencies, including the system, that we have battle-tested. There is also an unsupported, experimental :doc:`helm chart <helm>`,
not tested against current images.

For traditional Python environments, you can choose to :doc:`install from PyPI, using pip <python>`. This method
is more flexible but requires a working Python environment and some knowledge of Python.

If you want to :doc:`extend or contribute to HARP </contribute/index>`, consider :doc:`installing from sources
<sources>`.

-----

.. toctree::
    :maxdepth: 2
    :caption: Contents

    uv
    docker
    helm
    python
    sources


What next?
::::::::::

Once you're able to successfully run the proxy, you may want to head over to the
:doc:`Configuration </operate/configure/index>` section of the :doc:`/operate/index`.

You can also jump to one of the following guides:

.. include:: /_quicktoc.rst
