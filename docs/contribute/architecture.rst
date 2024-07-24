Architecture
============

Overview
::::::::

The codebase is divided into two main parts: Core and Applications. The Core provides the base functionality and tools
for building proxy services, while Applications (either built-in or user-provided) are independent modules that provide
the real features.

.. image:: ./overview.svg
    :alt: HARP Architecture Overview
    :align: center


Core
::::

* **ASGI** (:mod:`harp.asgi`): Building blocks for ASGI (Asynchronous Server Gateway Interface)
* **Command Line** (:mod:`harp.commandline`): Core commands and building blocks for application-specific commands.
* **Config** (:mod:`harp.config`): Configuration management system, supporting various formats and sources.
* **Controllers** (:mod:`harp.controllers`): Building blocks for web controllers, turning requests into responses.
* **HTTP** (:mod:`harp.http`): Building blocks for HTTP.
* **Meta** (:mod:`harp.meta`): Metadata management tools.
* **Models** (:mod:`harp.models`): Data modeling for core objects (not tied to storage logic, «plain old python objects»).
* **Typing** (:mod:`harp.typing`): Type and interface definitions.
* **Utils** (:mod:`harp.utils`): A collection of utility functions and helper classes that provide common functionality needed across the application.
* **Views** (:mod:`harp.views`): Presentation layer for controllers (should be merged?)


Sequence
::::::::

The schematic sequence of operations is as follows:

.. image:: ./sequence.svg
    :alt: HARP Sequence of Operations
    :align: center


Once the Services Provider is up, all services will be instanciated on a request basis, just in time.


Logging
:::::::

The logging system is based on the standard Python logging module, with a few customizations to fit our needs.

To use the logging system in your own modules, do the following:

.. code-block:: python

    from harp import get_logger

    logger = get_logger(__name__)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
