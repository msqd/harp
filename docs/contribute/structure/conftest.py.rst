conftest.py (optional)
======================

Conftest files are read by pytest for all tests under a given package to define fixtures. When defining fixtures for
an application's test, it's a good practice to scope them into this application package.

Dependencies
::::::::::::

If you need fixtures defined in another application's conftest file, you can simply import it from this conftest. It
has the free benefit of making the dependencies much more explicit.

To avoid having formatters remove this apparently unused import, add ``# noqa`` at the end of the line.

For example, if your application's tests depend on the storage application, you can add this to your application's
``conftest.py`` file:

.. code-block:: python

    from harp_apps.storage.conftest import *  # noqa

It is also possible if you're writing only some integrations test that use an optional dependency to add a
``conftest.py`` file with the dependency import in the integration test directory.
