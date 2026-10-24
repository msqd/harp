Prometheus
==========

.. versionadded:: 0.8

The prometheus integration exposes HARP's internal metrics in a format that prometheus can scrape. This format is
simple, text-based and human readable so it may even be useful outside of prometheus. The integration is provided by
the ``harp_apps.metrics`` application and is not enabled by default (as of version 0.8).


Setup
:::::

To enable it, use ``--enable metrics`` in the command line:

.. code:: bash

    harp-proxy server --enable metrics ...

The ``metrics`` application collects the metrics below. They are served by the dashboard, under ``/metrics`` (see
:ref:`below <prometheus-endpoint>`), never on the proxy ports: a ``/.prometheus/metrics`` request on a proxy port is
proxied to the upstream like any other path.


.. _storage-load-shedding:

Storage load shedding
:::::::::::::::::::::

When the storage queue backs up, HARP sheds observability instead of failing requests: bodies, then messages, then
whole transactions are not stored. A level engages only once the backlog has stayed at or above it for 2 seconds (see
:ref:`storage-recording-capacity`). Shedding is never silent:

* A warning is logged at most every 10 seconds, with the counts dropped since the previous warning.
* ``dropped_total{kind="transactions|messages|headers|bodies"}`` counts the same items.
* ``async_worker_queue_backlog`` reports the queue depth, 0 when the queue is empty.

These two metrics are always available on ``/metrics``, whether or not the ``metrics`` application is enabled.


.. _prometheus-endpoint:

Metrics endpoint
::::::::::::::::

``/metrics`` is served on the dashboard port (4080 by default) and follows the dashboard authentication. To also
serve it on a dedicated port, without authentication (off by default), set ``dashboard.metrics_port``:

.. code-block:: yaml

    dashboard:
      metrics_port: 9100

.. warning::

    The dedicated port has **no authentication**: anyone who can reach it reads your metrics. It binds all
    interfaces (``[::]``, like every HARP port) and its address is not configurable: ``dashboard.host`` does not apply to
    it. Restrict it outside HARP:
    a firewall or security group, a Kubernetes ``NetworkPolicy``, or, with Docker, publish it on loopback only
    (``-p 127.0.0.1:9100:9100``). Leave it unset to keep ``/metrics`` behind the dashboard authentication.


Metrics
:::::::

Metrics at the controller level (the middle layer, after the asgi kernel but before most of HARP's overhead):

* ``controller_requests_count``, a requests counter from the controller point of view.
* ``controller_requests_time``, an histogram of requests processing time.
* ``controller_requests_in_progress``, a gauge of requests currently being processed by a controller.
* ``controller_responses_count``, a controller responses counter.
* ``controller_exceptions_count``, an controller exceptions counter.

Metrics at the http client level (the innermost layer, when the proxy controller delegates to the http client).

* ``remote_requests_count``, a requests counter from the http client point of view.
* ``remote_requests_time``, an histogram of requests processing time.
* ``remote_requests_in_progress``, a gauge of requests currently being processed by the http client.
* ``remote_responses_count``, an http client responses counter.
* ``remote_exceptions_count``, an http client exceptions counter.

Additionally, a few python-related metrics and info are available, check the metrics endpoint.


Scrape configuration
:::::::::::::::::::::

Here is an example scrape configuration for prometheus, against the dashboard port. It follows the dashboard
authentication: add ``basic_auth`` credentials, or scrape ``dashboard.metrics_port`` instead.

.. code-block:: yaml

    scrape_configs:
      - job_name: harp
        honor_timestamps: true
        scrape_interval: 10s
        scrape_timeout: 10s
        metrics_path: /metrics
        scheme: http
        static_configs:
          - targets:
              - url.or.ip.for.harp.example.com:4080


.. seealso::

    - :doc:`Applications Reference » Metrics </apps/metrics/index>`



Scratchpad
::::::::::

**How many requests per second are being processed through harp server?**

.. code:: promql

    # everything that goes into a controller, averaged by 1 minute periods
    sum(rate(controller_requests_time_count[1m]))

.. code:: promql

    # everything that goes into the http client, including cached requests that does not
    # trigger an external request, averaged over 1 minute.
    sum(rate(remote_requests_time_count[1m]))

**Kernel overhead computation**
