Services
========

The ``harp.services`` package intergrate the :mod:`rodi` dependency injection container into the HARP framework, adding
helpers and utilities to make it easier to work with.

.. py:currentmodule:: harp.services

.. _service_container:
Container
:::::::::

.. todo::

    Container definition, allowing to configure the service graph, before compilation. Not everything has to be
    resolvable. You can't get instances yet.

    Add suggested public api methods (load, ...)

    Add life styles (singleton, transient, scoped, ...)


.. _service_definitions:
Service Definitions
:::::::::::::::::::

.. todo::

   A declarative way to define services, with their dependencies, life styles, etc. Allow to lazily reference other
   services, configuration values, etc.


.. _service_provider:
Provider
::::::::

.. todo::

    Once container.build_provider() is called, we have a provider that knows how to instanciate any service. The
    dependency graph has been resolved and checked, so we're confident you gan .get(...) instances. Errors may happen
    at instanciation time, but this is not the provider's responsibility.

    Add suggested public api methods (get, set, ...)


Configuration Reference
:::::::::::::::::::::::

.. todo::

    Add declarative configuration reference.

Types Reference
:::::::::::::::

Models
------

Providers
---------

References
----------

Resolvers
---------

Notes
:::::

Historically, we were using rodi's container directly in the core, but we decided to wrap it for a few reasons:

- automatic dependency injection from python typing annotations does not work well in rodi: it contains hacks based on
parameter names, and is subject to python type hints limitations making it hard to intergrate with third party libraries
(like httpx, which was the trigger for this change).
- we want some declarative way to integrate services
- we want injection to not be only kwargs based, but can be a mix
- we do not want the "all-or-nothing" approach of rodi, where you inject either all parameters automatically, or none.

We may switch the container implementation in the future, from rodi to some lightweight homemade implementation (or
not), but the current focus is to provide a stable API, the underlying implementation is somehow not important.
