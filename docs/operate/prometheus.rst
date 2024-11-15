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

    harp server --enable metrics ...

The ``metrics`` application will decorate the HARP ASGI implementation with a middleware that will expose the metrics
under the path ``/.prometheus/metrics``. You can configure your prometheus instance to scrape this path (see below).


Metrics
:::::::

Metrics at the ASGI handler level (the outermost layer, after the webserver interface):

* ``requests_count``, a requests counter.
* ``requests_time``, an histogram of requests processing time.
* ``requests_in_progress``, a gauge of requests currently being processed.
* ``responses_count``, a responses counter.
* ``exceptions_count``, an exceptions counter.

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

Here is an example scrape configuration for prometheus:

.. code-block:: yaml

    scrape_configs:
      - job_name: harp
        honor_timestamps: true
        scrape_interval: 10s
        scrape_timeout: 10s
        metrics_path: /.prometheus/metrics
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

    # everything that goes into harp server, averaged by 1 minute periods
    sum(rate(requests_time_count[1m]))

.. code:: promql

    # everything that goes into a controller, averaged by 1 minute periods
    sum(rate(controller_requests_time_count[1m]))

.. code:: promql

    # everything that goes into the http client, including cached requests that does not
    # trigger an external request, averaged over 1 minute.
    sum(rate(remote_requests_time_count[1m]))

**Kernel overhead computation**
