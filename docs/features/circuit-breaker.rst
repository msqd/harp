Circuit Breaker
===============

.. versionadded:: 0.7

Interactions with remote resources can fail due to issues like slow network connections, timeouts, or temporary
unavailability. Some faults are short-lived and can be mitigated using :doc:`retry strategies <./retry>`, but longer
failures need different handling.

To handle long-term remote service failures, your proxies can leverage a
`Circuit Breaker <https://harp-project.net/patterns/circuit-breaker>`_ to lower pressure and responsiveness of API calls
to failing remote services.

Each endpoint has a pool of remote URLs, used in a round-robin manner as long as there are no failures.

.. literalinclude:: ../apps/proxy/examples/pooled.yml
    :language: yaml

When a failure is detected with one of the URLs, the circuit breaker opens (meaning traffic won't go through this URL
anymore), and a fallback pool is eventually used if there aren't enough URLs left.

.. literalinclude:: ../apps/proxy/examples/pooled-fallback.yml
    :language: yaml

If no URLs are available in the active pool, the proxy returns a 503 error code to the client until the circuit breaker
"closes" again for an URL.

After a configurable delay, the circuit breaker will try to close for the failing URL by switching to the half-open
state. This is an intermediate state where the URL is tested again, and if it fails, the circuit breaker reopens. If the
attempt is successful, the circuit breaker closes, and the URL is added back to the active pool (if criteria are met).

To reduce the amount of errors passing through, it is possible to setup a probe that will run on a regular basis to
verify the health status of all endpoints. Please note that even URLs that are not in the active pool are probed,
to be able to switch if they are added to the pool.

.. literalinclude:: ../apps/proxy/examples/pooled-healthcheck.yml
    :language: yaml

The circuit breaker conditions for failure are configurable, using a set of named criteria:

.. literalinclude:: ../apps/proxy/examples/pooled-aggressive.yml
    :language: yaml

In this case, the circuit breaker will consider as failed all URLs that either fail on the network level, or send back
a 4xx or 5xx status code. It's generally not a good idea to include 4xx codes here, as it denotes a client error, but if
you do need it and know what you're doing, you can.

The circuit breaker is **disabled** in the default configuration, and should be enabled using a liveness algorithm
selection (good candidates are ``leaky`` or ``naive``).

Configuration
-------------

Configure the circuit breaker for each proxy endpoint under ``proxy.endpoints[].remote``.
The ``liveness`` setting selects the algorithm, ``break_on`` selects which request failures
count against a remote URL, and the optional ``probe`` checks remote health in the background.
See the :doc:`proxy settings reference <../apps/proxy/settings>` for the full configuration.

.. code-block:: yaml

    proxy:
      endpoints:
        - name: example
          port: 4000
          remote:
            endpoints:
              - url: "https://api.example.com/"
            liveness:
              type: naive
              failure_threshold: 3
              success_threshold: 2
            break_on: [network_error, unhandled_exception, http_5xx]
            probe:
              method: GET
              path: /health
              interval: 10.0
              timeout: 5.0

This example marks a URL as down after three consecutive failures and restores it after two
consecutive successes. A successful request or probe resets the failure count; a failure resets
the success count. Probes consider HTTP 2xx and 3xx responses successful, independently of
``break_on``, which controls failures from proxied requests.

Liveness algorithms
~~~~~~~~~~~~~~~~~~~

Set ``liveness.type`` to ``naive`` to count consecutive failures and successes:

.. list-table:: Naive options
    :header-rows: 1
    :widths: 25 15 60

    * - Option
      - Default
      - Meaning
    * - ``failure_threshold``
      - ``1``
      - Consecutive failures needed to mark a URL as down. Must be greater than zero.
    * - ``success_threshold``
      - ``1``
      - Consecutive successes needed to mark a URL as up. Must be greater than zero.

Set ``liveness.type`` to ``leaky`` to accumulate failures in a bucket that drains over time.
Each failure adds one to the bucket, up to its capacity. A failure marks the URL as down when
the level reaches the threshold; a success marks it as up when the level is below the threshold.

.. list-table:: Leaky bucket options
    :header-rows: 1
    :widths: 25 15 60

    * - Option
      - Default
      - Meaning
    * - ``rate``
      - ``1.0``
      - Amount drained from the bucket per second.
    * - ``capacity``
      - ``60.0``
      - Maximum bucket level.
    * - ``threshold``
      - ``10.0``
      - Bucket level at which a failure marks the URL as down.
