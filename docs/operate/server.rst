ASGI server
===========

HARP serves its ports with an ASGI server. Choose it at startup with ``--server`` or the ``HARP_SERVER`` environment
variable:

.. code-block:: shell

    harp-proxy server --server hypercorn
    HARP_SERVER=uvicorn harp-proxy server

Available servers
:::::::::::::::::

.. list-table::
    :header-rows: 1
    :widths: 22 78

    * - Name
      - Notes
    * - ``hypercorn+uvloop``
      - The default (``hypercorn`` on Windows). Hypercorn on the `uvloop <https://github.com/MagicStack/uvloop>`_ event
        loop. Keeps HTTP/2, and logging through HARP's configuration.
    * - ``hypercorn``
      - Hypercorn on the standard asyncio loop.
    * - ``uvicorn``
      - Uvicorn with httptools, on uvloop. HTTP/1.1 only. Needs the ``servers`` extra.
    * - ``granian``
      - Granian's embedded server (experimental upstream). No access log, and one listener per port: a port other than
        the first may answer 500 for a few milliseconds before startup completes. Needs the ``servers`` extra.

An unknown name is refused with the list of valid ones. ``harp-proxy start`` forwards the option to the server it
launches.

The ``uvicorn`` and ``granian`` servers come with an extra:

.. code-block:: shell

    pip install harp-proxy[servers]

uvloop and Windows
::::::::::::::::::

uvloop replaces the asyncio event loop with a faster one. It does not exist on Windows (nor Cygwin), so it is not
installed there, and the default server is plain ``hypercorn``. Asking for a uvloop server (``hypercorn+uvloop``,
``uvicorn``) where uvloop is missing does not fail: HARP logs one warning naming the server and the platform and runs
on the asyncio loop.

Choosing
::::::::

Keep the default unless you have a reason. ``uvicorn`` and ``granian`` are there for comparison; measure with your own
traffic before moving. See ``bench/FINDINGS.md`` in the repository for the numbers measured so far (laptop runs, only
indicative).
