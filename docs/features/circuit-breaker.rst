Circuit Breaker
===============

In distributed systems, interactions with remote resources can fail due to issues like slow network connections,
timeouts, or temporary unavailability. While some faults are short-lived and can be fixed with retry strategies,
others last longer and need different handling to avoid wasting resources.

To handle long-term remote service failures, HARP Proxy uses the
`Circuit Breaker pattern <https://harp-proxy.net/patterns/circuit-breaker>`_.

Each endpoint has a pool of remote URLs, used in a round-robin manner as long as there are no failures.

.. literalinclude:: ../apps/proxy/examples/pooled.yml
    :language: yaml

When a failure is detected with one of the URLs, the circuit breaker opens (meaning traffic won't go through this URL
anymore), and a fallback pool is eventually used if there aren't enough URLs left.

.. literalinclude:: ../apps/proxy/examples/pooled-fallback.yml
    :language: yaml

If no URLs are available in the active pool, the proxy returns a 503 error code to the client until the circuit breaker
"closes" again.

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

In this case, the circuit breaker wiill consider as failed all URLs that either fail on the network level, or send back
a 4xx or 5xx status code. It's generally not a good idea to include 4xx codes here, as it denotes a client error, but if
you do need it and know what you're doing, you can.

The circuit breaker is enabled with reasonable settings and no probe in the default configuration.
