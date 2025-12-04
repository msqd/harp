Configuration
=============

.. versionadded:: 0.5

Configuration in HARP is dynamically built from various sources, with each subsequent source having the ability to
override the previous ones. This design ensures maximum flexibility and adaptability to different environments and
deployment scenarios.

.. figure:: /operate/configure/overview.svg
   :alt: Configuration Sources
   :align: center

The sources of configuration, listed from the lowest to the highest precedence, are:

- **Default Settings**: These are predefined values within HARP Core and HARP Applications (both built-in and
  user-provided). They establish a foundational configuration that allows the service to operate with minimal initial
  setup.

- **Configuration Files**: These files offer a structured and version-controllable method to define generic and/or
  environment-specific configurations (e.g., for development, testing, production environments). They have higher
  precedence than default settings, allowing for easy adjustments across different environments.

- **Environment Variables**: Used for overriding configurations in specific instances, such as cloud deployments or
  when managing sensitive information that should not be included in version control. Environment variables have higher
  precedence over configuration files, offering the flexibility to modify settings without changing application code or
  configuration files.

- **Command Line Arguments**: These provide the highest level of immediacy and flexibility, allowing operators to
  override any other configuration source for specific use cases, debugging, or runtime conditions. Command line
  arguments enable behavior changes without the need to alter the environment setup or deployment configurations.

Each HARP Application defines its own set of configuration settings, detailed within the respective application's
documentation section:

* :doc:`Dashboard </apps/dashboard/index>`: Web interface configuration and features.
* :doc:`Http Client </apps/http_client/index>`: Configuration for timeouts, caching, and other HTTP client behaviors.
* :doc:`Janitor </apps/janitor/index>`: Settings for housekeeping tasks and maintenance operations.
* :doc:`Proxy & Endpoints </apps/proxy/index>`: Configuration for endpoints, names, ports, and routing.
* :doc:`Storage </apps/storage/index>`: Settings for managing relational and non-relational storage solutions.
* :doc:`Telemetry </apps/telemetry/index>`: Configuration for usage reporting and telemetry data collection.
* :doc:`Rules Engine </apps/rules/index>`: Fine-tuning and configuration of the request lifecycle through rules.

Application Filtering
---------------------

.. versionadded:: 0.10

Applications can be selectively enabled or disabled through configuration, allowing you to customize
which components are loaded at runtime. This is useful for environment-specific configurations or
when certain applications are not needed.

Disabling Applications
^^^^^^^^^^^^^^^^^^^^^^^

To disable an application, set ``enabled: false`` at the application's root level in your configuration:

.. code-block:: yaml

    # config.yaml
    storage:
        enabled: false  # Storage application will not be loaded
        database_url: "postgresql://..."  # Configuration preserved but unused

    http_client:
        enabled: false  # HTTP client will not be loaded

When an application is disabled:

- The application is not loaded into the system
- Its event handlers are not registered
- Its services are not available for dependency injection
- A warning is logged: ``Application '{name}' is disabled as per configuration directive``

.. note::
   Disabled applications can still have their configuration preserved in the file. This allows
   you to toggle applications on/off without losing their settings.

Unknown Applications
^^^^^^^^^^^^^^^^^^^^

If your configuration file contains settings for an application that is not loaded or does not exist,
HARP will issue a warning:

.. code-block:: text

    Configuration found for application 'unknown_app' which is not loaded.
    This may be strictly enforced in future versions.

This helps detect typos or outdated configuration entries.

Strict Mode
^^^^^^^^^^^

The ``--strict`` flag makes configuration validation more rigorous. When enabled, configuration
for unknown applications will raise an error instead of a warning:

.. code-block:: bash

    # Normal mode - warnings only
    $ harp-proxy server

    # Strict mode - errors for unknown apps
    $ harp-proxy server --strict

Use strict mode in:

- **CI/CD pipelines**: Catch configuration issues early
- **Production deployments**: Ensure configuration matches expected applications
- **Configuration validation**: Verify config files are correct

Example: Environment-Specific Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    # production.yaml
    dashboard:
        enabled: false  # No dashboard in production

    storage:
        enabled: true
        database_url: "postgresql://prod-db:5432/harp"

    telemetry:
        enabled: true
        endpoint: "https://telemetry.example.com"

.. code-block:: yaml

    # development.yaml
    dashboard:
        enabled: true  # Dashboard available for developers

    storage:
        enabled: true
        database_url: "sqlite:///dev.db"

    telemetry:
        enabled: false  # No telemetry in development

Debug Mode
----------

.. versionadded:: 0.10

HARP provides a debug mode that enables additional diagnostic information. This is controlled via
environment variables:

- ``HARP_DEBUG``: The primary environment variable for enabling debug mode
- ``DEBUG``: Alternative environment variable (for compatibility)

When debug mode is enabled (``harp.DEBUG`` is truthy):

- Error responses include full exception tracebacks
- Additional diagnostic information may be included in outputs

.. warning::

   **Do not enable debug mode in production environments.** Exception tracebacks may contain
   sensitive information such as file paths, internal variable values, database queries, or
   other implementation details that could aid attackers.

Example usage:

.. code-block:: bash

    # Enable debug mode
    $ HARP_DEBUG=1 harp-proxy server

    # Or using the DEBUG variable
    $ DEBUG=1 harp-proxy server

You can also check the debug status programmatically:

.. code-block:: python

    import harp

    if harp.DEBUG:
        print("Debug mode is enabled")
