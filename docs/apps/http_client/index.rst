HttpClient
==========

The `harp_apps.http_client` application implements the core HTTP client features. It uses caching to store responses and avoid making the same request multiple times, improving the efficiency of your application.
The caching mechanism is implemented using `Hishel <https://hishel.com/>`_ a powerful caching library.

Overview
--------

The HTTP client provides efficient and configurable HTTP request handling with caching capabilities.
It is designed to be integrated seamlessly into the `harp` framework.

Features
--------

- **Caching:** Reduces redundant network calls by storing responses.
- **Configurable Timeouts:** Allows setting custom timeout values for requests.
- **Flexible Cache Settings:** Offers options to configure cacheable methods and status codes.

Loading
-------

The HTTP client application is loaded by default when using the `harp start` command.

Configuration
-------------

Below is an example configuration for the HTTP client:

.. literalinclude:: ./examples/http_client_settings.yml
    :language: yaml



- **timeout:** Specifies the request timeout duration in seconds (default: 30 seconds).
- **cache:** Configuration for caching behavior.
  - **disabled:** Boolean flag to enable or disable caching.
  - **cacheable_methods:** List of HTTP methods that can be cached (e.g., GET).
  - **cacheable_status_codes:** List of HTTP status codes that can be cached (e.g., 200, 300).

Internal Implementation
-----------------------

The internal implementation leverages the following classes:

- :class:`CacheSettings <harp_apps.http_client.settings.CacheSettings>`
- :class:`HttpClientSettings <harp_apps.http_client.settings.HttpClientSettings>`
