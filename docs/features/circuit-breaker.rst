Circuit Breaker
===============

In distributed systems, interactions with remote resources can fail due to issues like slow network connections,
timeouts, or temporary unavailability. While some faults are short-lived and can be mitigated with retry strategies,
others are more persistent and require different handling to avoid resource wastage.

HARP Proxy implements the Circuit Breaker pattern by detecting failures and preventing repeated attempts to perform
operations likely to fail, thus maintaining system stability and preventing cascading failures.

More informations are available in the :ref:`Proxy / Circuit Breaker Feature <circuit-breaker>` documentation.
