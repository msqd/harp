HTTP Client
===========

.. tags:: applications

.. versionadded:: 0.5

The `harp_apps.http_client` application implements the core HTTP client features. It uses caching to store responses
and avoid making the same request multiple times, improving the efficiency of your application.

The application wioll mostly define a coherent set of :doc:`services <services>` that will be used to interact with external http
services, allowing other mechanisms to hook into the request/response lifecycle (cache, rules, ...).

The caching mechanism is implemented using `Hishel <https://hishel.com/>`_ a powerful caching library.

.. toctree::
    :hidden:
    :maxdepth: 1

    Events <events>
    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.http_client>


Overview
::::::::

The HTTP client provides efficient and configurable HTTP request handling with caching capabilities.
It is designed to be integrated seamlessly into the ``harp`` framework.

Features
::::::::

- **Caching:** Reduces redundant network calls by storing responses.
- **Configurable Timeouts:** Allows setting custom timeout values for requests.
- **Flexible Cache Settings:** Offers options to configure cacheable methods and status codes.

Loading
:::::::

The HTTP client application is loaded by default when using the `harp start` command.

Configuration
:::::::::::::

Below is an example configuration for the HTTP client:

.. literalinclude:: ./examples/simple.yml
    :language: yaml

You can refer to `hishel.Controller documentation <https://hishel.com/advanced/controllers/>`_ for all available
options.


- **timeout:** Specifies the request timeout duration in seconds (default: 30 seconds).

- **cache:** Configuration for caching behavior.

  - **disabled:** Boolean flag to enable or disable caching.

  - **controller:** Configuration for controller settings.

    - **allow_stale:** Boolean flag to allow serving stale cache data when the cache is expired (default: False).

    - **allow_heuristics:** Boolean flag to allow heuristic caching (default: False).

    - **cacheable_methods:** List of HTTP methods that can be cached (e.g., GET).

    - **cacheable_status_codes:** List of HTTP status codes that can be cached (e.g., 200, 300).

Internal Implementation
:::::::::::::::::::::::

The internal implementation leverages the following classes:

- :class:`ControllerSettings <harp_apps.http_client.settings.ControllerSettings>`

- :class:`CacheSettings <harp_apps.http_client.settings.CacheSettings>`

- :class:`HttpClientSettings <harp_apps.http_client.settings.HttpClientSettings>`

Full example
::::::::::::

.. literalinclude:: ./examples/full.yml
    :language: yaml
