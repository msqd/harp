Customize
=========

Most HARP features can be customized through configuration files without writing any code. This is the recommended approach for most use cases.


Configuration-first approach
:::::::::::::::::::::::::::::

HARP supports extensive customization through YAML configuration files:

- **Endpoints and routing**: Define proxies, ports, and target URLs
- **HTTP client behavior**: Timeouts, retries, caching, connection pooling
- **Storage backends**: SQLite, PostgreSQL, MySQL, Redis
- **Transaction lifecycle**: Custom scripts for request/response processing
- **Dashboard and monitoring**: Enable and configure the web UI
- **Authentication**: Basic auth, custom authentication handlers

For complete configuration reference, see :doc:`Configuration guide </operate/configure/index>`.


Transaction lifecycle customization
::::::::::::::::::::::::::::::::::::

The :doc:`Rules engine </apps/rules/index>` allows you to customize request and response handling using Python scripts embedded in your configuration:

.. code:: yaml

    rules:
      on_request: |
        # Modify requests before forwarding
        request.headers['X-Custom-Header'] = 'value'

      on_response: |
        # Modify responses before returning to client
        response.status_code = 200

This approach requires no custom applications - just configuration.


When to use programmatic customization
:::::::::::::::::::::::::::::::::::::::

Consider writing custom code when you need:

- Complex business logic that doesn't fit in configuration scripts
- Integration with external services or libraries
- Custom storage backends or service implementations
- Reusable components across multiple projects

For these cases, see :doc:`extend` to learn about creating custom HARP applications.
