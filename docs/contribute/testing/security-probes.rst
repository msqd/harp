Security probes
===============

The security fixes are unit tested. The probes replay them against a **running** ``harp-proxy server`` over a raw
socket, with an origin that records the exact bytes it received: malformed request lines and ambiguous framing do not
survive a normal HTTP client.

.. code-block:: shell

    make test-security-probes

They are not part of ``make test``: their files are named ``probe_*.py``, which a plain ``pytest`` does not collect.
Probe 5 pulls a PostgreSQL container, so Docker must be available.

Every probe records the conditions its reading was taken under (the storage backend, the environment) and the run prints
them after the verdict. A probe that depends on a condition it does not control refuses to report instead of
reassuring: probe 5 fails when ``FORCE_COLOR`` or ``NO_COLOR`` is set in its environment. The Makefile target unsets both.

What each probe asserts
-----------------------

.. list-table::
    :header-rows: 1

    * - Probe
      - Asserts on ``main``
      - Negative control
    * - 1. Scheme in path (CWE-918)
      - ``GET /http://example.org/`` and ``GET //example.org/`` reach the configured origin, and only it, as a path
      - ``48261dce``
    * - 2. Dot segments
      - ``GET /../../admin`` on a subtree endpoint is answered 400, the origin is not reached, a control request is
        forwarded under the prefix
      - ``48261dce``
    * - 3. ``Content-Length`` with ``Transfer-Encoding``
      - 400 with ``Connection: close``, the origin is not reached, a single framing is forwarded whole
      - ``87dfced3``
    * - 4a. Hop-by-hop, request
      - ``TE``, ``Trailer``, ``Upgrade``, ``Proxy-Authorization``, ``Keep-Alive``, the header named by ``Connection`` and a
        spoofed ``X-Forwarded-For`` do not reach the origin, ordinary headers do
      - ``87dfced3``
    * - 4b. Hop-by-hop, response
      - the same, from the origin to the client
      - ``0.10.0``
    * - 5. Credential masking
      - ``system config`` (default, ``--raw``, ``--json``) and ``GET /api/system/proxy``, logged in or not, never print
        the storage, endpoint or dashboard password; ``--unsecure`` still does
      - ``bf1a4cdf``

Checking a probe against its vulnerable commit
----------------------------------------------

A probe that cannot fail proves nothing. Check out the negative control in a separate worktree, copy ``tests/security_probes``
into it and run the same command: the probe must fail on the assertion naming the vulnerability, not on setup.

.. code-block:: shell

    git worktree add ../harp-control 87dfced3
    cp -r tests/security_probes ../harp-control/tests/
    cd ../harp-control && uv run pytest -o python_files='probe_*.py' tests/security_probes/probe_framing.py
