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
- **transport:** The base HTTP transport implementation (default: ``harp_apps.http_client.aiohttp_transport.AiohttpTransport``)
- **proxy_transport:** The proxy transport wrapper (default: ``AsyncFilterableTransport``)

Alternative transports
::::::::::::::::::::::

``transport.type`` takes the full class path of any httpx ``AsyncBaseTransport``. The default is
``harp_apps.http_client.aiohttp_transport.AiohttpTransport``, which sends requests with aiohttp instead of httpcore. To
get httpx's own transport back (HTTP/2 upstream, retries, a CA path as ``verify``, ``max_keepalive_connections``):

.. code-block:: yaml

    http_client:
      transport:
        type: httpx.AsyncHTTPTransport

``harp_apps.http_client.pyreqwest_transport.PyreqwestTransport`` (reqwest, in Rust; ``pyreqwest`` extra) is
non-conforming and exists for benchmarking only: it does not keep the order of headers across names, the interleaving
of duplicates or their casing, and adds ``Accept`` and ``User-Agent`` when the request has none. Do not use it to
serve traffic.

A transport must keep headers as given (order, duplicates, casing), add none, hand the body over undecoded, follow no
redirects, and raise the httpx exceptions for timeouts and network errors. The common arguments are ``verify``,
``retries`` and ``limits`` (``httpx.Limits``); the timeout comes from the client. A transport honours them or refuses
them at startup. The aiohttp one refuses ``retries`` above 0, ``limits.max_keepalive_connections`` and a ``verify``
that is neither a boolean nor an ``ssl.SSLContext``, and ``http2``, ``http1: false``, ``cert``, ``proxy``, ``uds``, ``local_address``, ``socket_options`` and ``trust_env``, with a message
naming ``httpx.AsyncHTTPTransport``. ``verify: true`` trusts certifi, like httpx. The ``write`` timeout is not applied and
responses always report HTTP/1.1.

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
