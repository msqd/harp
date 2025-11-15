Introduction
============

HARP is designed to be extended and customized to fit your needs. You can contribute to the core, build custom
applications, or extend existing functionality through various extension points.

Extension possibilities
:::::::::::::::::::::::

**Custom applications**
    Build standalone applications that integrate with HARP's plugin system. Applications can provide new features,
    endpoints, or services. See :doc:`applications` for details.

**Event listeners**
    Hook into HARP's event-driven architecture to react to system events, HTTP transactions, or application lifecycle
    events. See :doc:`events` for details.

**Dependency injection**
    Register custom services and dependencies through the IoC container to make them available system-wide. See
    :doc:`dependency-injection` for details.

**Storage backends**
    Implement custom storage backends for transactions, configuration, or application-specific data. See
    :doc:`storage/index` for details.

**Dashboard extensions**
    Extend the web dashboard with custom views, components, or pages. See :doc:`../apps/dashboard/development/index`
    for details.


Getting started
:::::::::::::::

To start contributing or extending HARP:

1. **Set up your development environment** - Follow the :doc:`setup` guide to install dependencies and run HARP locally.
2. **Understand the architecture** - Read the :doc:`overview` to grasp high-level concepts and patterns.
3. **Explore specific topics** - Dive into :doc:`applications`, :doc:`events`, :doc:`dependency-injection`, or other
   areas relevant to your work.
4. **Write tests** - Follow the :doc:`testing/index` guidelines to ensure your code is well-tested.


Developer resources
:::::::::::::::::::

- **Makefile** - Common development tasks are available through ``make``. Run ``make help`` to see available commands.
- **Command line** - The ``uv run harp`` command provides access to all HARP CLI tools within the development
  environment. See :doc:`/commandline/index` for reference.
- **Release process** - If you're preparing releases, see :doc:`release/index` for guidelines.
