Getting Started
===============

This guide contains eveything you need to download install and run HARP Proxy.

.. toctree::
    :maxdepth: 2

    quick


Installation
::::::::::::

Several options exist to install HARP Proxy on your development machine.

The **recommended** method is :doc:`using UV <uv>`, a fast Python package manager that makes installation and execution simple.

For containerized environments, you can use :doc:`Docker containers <docker>`, ensuring you have the exact set of
dependencies, including the system, that we have battle-tested. There is also an :doc:`helm chart <helm>` available for
kubernetes users.

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
