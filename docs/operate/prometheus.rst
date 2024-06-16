Prometheus
==========

.. warning::

    This feature is mostly for internal use for now, and although we'll keep a prometheus integration in the future,
    configuration will change.

Enable the middleware using ...

.. code-block:: bash

    USE_ASGI_PROMETHEUS_MIDDLEWARE=true harp ...

Then you can access the metrics at ``/.prometheus/metrics``.

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
