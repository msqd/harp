HTTP Client
===========

.. tags:: applications

.. versionadded:: 0.5

.. versionchanged:: 0.10

    Caching functionality was extracted to the separate :doc:`http_cache </apps/http_cache/index>` application.

The ``harp_apps.http_client`` application implements the core HTTP client features for making HTTP requests to
external services.

The application defines a coherent set of :doc:`services <services>` that are used to interact with external HTTP
services, allowing other mechanisms to hook into the request/response lifecycle (cache, rules, ...).

For HTTP caching functionality, see the :doc:`http_cache </apps/http_cache/index>` application, which provides
RFC 9111-compliant caching using `Hishel 1.0 <https://hishel.com/>`_.

.. toctree::
    :hidden:
    :maxdepth: 1

    Events <events>
    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.http_client>


Overview
::::::::

The HTTP client provides efficient and configurable HTTP request handling for making requests to external
services. It is designed to be integrated seamlessly into the ``harp`` framework and supports extensibility
through transport wrappers.

Features
::::::::

- **Async HTTP Client:** Built on `httpx <https://www.python-httpx.org/>`_ for high-performance async requests
- **Configurable Timeouts:** Allows setting custom timeout values for requests
- **Transport Layer:** Flexible transport architecture supporting middleware and extensions
- **Event System:** Hooks for request/response lifecycle events
- **Extensible:** Supports integration with caching, rules, and other applications

Loading
:::::::

The HTTP client application is loaded by default when using the `harp-proxy start` command.

Configuration
:::::::::::::

Below is an example configuration for the HTTP client:

.. literalinclude:: ./examples/simple.yml
    :language: yaml

Configuration options:

- **timeout:** Specifies the request timeout duration in seconds (default: ``30.0``)
- **transport:** The base HTTP transport implementation (default: ``httpx.AsyncHTTPTransport``)
- **proxy_transport:** The proxy transport wrapper (default: ``AsyncFilterableTransport``)

For caching configuration, see the :doc:`http_cache </apps/http_cache/index>` application documentation.

Internal Implementation
:::::::::::::::::::::::

The internal implementation leverages the following classes:

- :class:`HttpClientSettings <harp_apps.http_client.settings.HttpClientSettings>` - Client configuration
- :class:`AsyncFilterableTransport <harp_apps.http_client.transports.AsyncFilterableTransport>` - Transport wrapper

For cache implementation details, see the :doc:`http_cache </apps/http_cache/index>` application.

Full example
::::::::::::

.. literalinclude:: ./examples/full.yml
    :language: yaml
