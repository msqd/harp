Command Line
============

Start
:::::

Starts local dev services using honcho (only for development purposes).

.. code-block:: bash

    $ harp start [--with-docs/--no-docs] [--with-ui/--no-ui] [services...] [--set <key>=<value> ...] [--file/-f <config-file> ...] [--server-subprocess/-XS <command> ...]


Available services:

- server
- dashboard
- docs
- ui

By default, `harp start` will start the server and the dashboard.

.. todo::

    Undocumented (for now)

    - --server-subprocess
    - install-dev

    Possible future things

    - build (compile stuff for production)
    - serve (run a production-like server)

    Document how harp start work (honcho, devserver port, ...)
