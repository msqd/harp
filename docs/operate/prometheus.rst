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

Default metrics provided by harp's ``metrics`` application are:

* ``requests_count``, a requests counter (labels: method, path).
* ``requests_time``, an histogram of requests processing time by path (labels: method, path).
* ``requests_in_progress``, a gauge of requests by method and path currently being processed (labels: method, path).
* ``responses_count``, a responses counter (labels: status, method, path).
* ``exceptions_count``, an exceptions counter (labels: exception, method, path).

* ``proxy_requests_count`` is a requests counter from the proxy controller point of view (labels: method, path).
* ``proxy_requests_time`` is an histogram of requests processing time by path (labels: method, path).
* ``proxy_requests_in_progress`` is a gauge of requests by method and path currently being processed (labels: method, path).
* ``proxy_responses_count`` is a responses counter (labels: status, method, path).



Additionally, a few python-related metrics and info are available, check the metrics endpoint.

* ``harp_asgi_*``: asgi kernel measurements (the outermost layer, after the webserver interface).
* ``harp_proxy_*``: proxy controller measurements (the middle layer, after the asgi kernel but before most of
  harp's overhead).
* ``harp_remote_*``: remote requests measurements (the innermost layer, when the proxy controller delegates to
  the http client for a potential remote request).


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
