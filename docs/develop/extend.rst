Extend
======

When configuration alone isn't enough, you can extend HARP by creating custom applications. A HARP application is a standard Python package with lifecycle hooks and dependency injection support.


What are HARP applications?
::::::::::::::::::::::::::::

HARP applications are Python packages that integrate with HARP's lifecycle and dependency injection system. They can:

- Add custom controllers and routes
- Implement custom storage backends
- Provide reusable services
- Hook into request/response processing
- Extend the dashboard UI


Learning from built-in applications
::::::::::::::::::::::::::::::::::::

The best way to learn is by examining HARP's built-in applications in ``harp_apps/``:

- **proxy** (``harp_apps.proxy``): HTTP proxy with connection pooling and health checks
- **http_client** (``harp_apps.http_client``): HTTP client with caching and retry logic
- **storage** (``harp_apps.storage``): Database backends (SQLite, PostgreSQL, MySQL, Redis)
- **dashboard** (``harp_apps.dashboard``): Web UI with React frontend
- **rules** (``harp_apps.rules``): Transaction lifecycle scripting engine

Each application has an ``__app__.py`` file defining its lifecycle hooks. For example, see ``harp_apps.acme/__app__.py`` for a minimal application template.


Creating your own application
::::::::::::::::::::::::::::::

1. Generate a project with application support:

   .. code:: shell

       uvx --python 3.13 harp-proxy create project

   Answer "yes" when asked about creating an application folder.

2. Define your application in ``your_app/__app__.py``:

   .. code:: python

       from harp.config import Application

       application = Application(
           on_bind=...,    # Register services in DI container
           on_bound=...,   # Configure services after DI resolution
           on_ready=...,   # Initialize when server starts
           on_shutdown=..., # Cleanup on shutdown
       )

3. Enable your application:

   .. code:: shell

       uv run harp-proxy server --enable your_app


Detailed documentation
:::::::::::::::::::::::

For comprehensive guides on application development, see:

- :doc:`Application protocol </contribute/applications>` - Basic structure and settings
- :doc:`Application structure </contribute/structure/index>` - File organization and conventions
- :doc:`Dependency injection </contribute/dependency-injection>` - Service registration and resolution
- :doc:`Events </contribute/events>` - Lifecycle hooks and event handling
- :doc:`Testing </contribute/testing/index>` - Testing applications and fixtures
