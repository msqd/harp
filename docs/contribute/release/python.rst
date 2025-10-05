Releasing as a Python Package
=============================

Releasing a python package for a version consists of building a wheel, testing it and pushing it to the Python Package
Index (PyPI).

.. note::

    The release process is now automated via GitHub Actions! When you push a version tag (e.g., ``0.9.0``), the
    workflow automatically builds, tests, and publishes the package. See :doc:`pypi-trusted-publishing` for setup
    instructions.

    The manual process below is still documented for reference or emergency situations.


Building a wheel
::::::::::::::::

To build a wheel in an isolated directory:

.. code-block:: shell

    make clean-dist wheel

The resulting build artifacts (wheel, tgz ...) will be available under the dist/ directory of your working copy.


Testing a wheel
:::::::::::::::

To test a wheel you just built, a script is available to run a brand new container and pip install it (from filesystem):

.. code-block:: shell

    bin/runc_wheel dist/*.whl

Once your container is up and running, you can run a server using, for example:

.. code-block::

    harp server --endpoint httpbin=4000:http://httpbin.org/


Releasing a wheel to PyPI
:::::::::::::::::::::::::

Once you're confident with the just built wheel, it's time to make it available to the outside world. You will need
`twine` to be installed on your system (for example, using homebrew).

.. code-block::

    twine upload dist/*
