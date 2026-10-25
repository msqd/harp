Run
===

.. note::

    This document describes the live deployment options. If you're looking for a guide on how to run harp locally,
    please refer to the :doc:`run section of the developer's guide <../develop/run>`.

Launch
::::::

In production, ``harp-proxy server`` is the only process you run. It serves the proxy ports and the
:doc:`dashboard </apps/dashboard/index>` (API and compiled frontend) from one Python process and one event loop. To
scale out, run more instances behind a load balancer, all pointing at the same PostgreSQL
(:doc:`storage </apps/storage/index>`).

.. code-block:: shell

    harp-proxy server --file /etc/harp.yaml

Configuration comes from files, ``HARP_*`` environment variables and ``--set`` options, in that order of increasing
precedence (see :doc:`configure/index`). In a container, use ``docker run --init`` (see :doc:`/start/docker`); the
image runs as the unprivileged user ``harp`` and its health check calls ``/healthz``.

Ports
:::::

Every endpoint of ``proxy.endpoints`` listens on its own ``port``. The dashboard listens on ``dashboard.port`` (4080
by default) and, when set, ``dashboard.metrics_port`` serves the metrics. What each port exposes and how to restrict
it is in :doc:`security`.
