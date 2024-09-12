Janitor
=======

.. tags:: applications

.. versionadded:: 0.5

The ``janitor`` application runs a background worker to clean up the storage. It deletes all transactions older than 2
months, and the related orphan blobs.

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.janitor>


Defaults
::::::::

Runs every 10 minutes.

Delete all transactions older than 60 days.

.. note:: for now, this is not configurable but will be in the near future.

Loading
:::::::

The proxy application is loaded by default when using the ``harp start`` command.

You can disable it (not recommended) by passing it as an argument to the ``harp start`` command:

.. code-block:: bash

    harp start --disable janitor ...
