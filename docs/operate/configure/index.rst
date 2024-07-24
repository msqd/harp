Configuration
=============

Configuration in HARP is dynamically built from various sources, with each subsequent source having the ability to
override the previous ones. This design ensures maximum flexibility and adaptability to different environments and
deployment scenarios.

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
