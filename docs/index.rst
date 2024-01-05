Harp — HTTP API Runtime Proxy
=============================

Harp is a tiny and fast sidecar microservice that stands by between your application and an
external API to add features (like caching, retrying, auditing, debugging, rewriting, ...)
without having add code on your application side.

Content
:::::::

.. toctree::
   :maxdepth: 2

   quickstart/index
   installation/index
   configuration/index
   features/index
   reference/index
   development/index
   faq
   gotchas

Introduction
::::::::::::

Harp is written in Python and Cython (kind of a Python to C++ transpiler) and compiled to
native bytecode for blazing speed.

Harp also provides a management API and an optional frontend that helps you display and
explore logs, debug HTTP calls (with breakpoints) and much more.

Harp can be used both as a development and a production tool, for different purposes.

Harp uses a dual licence model:

- The basic version is open-source and can be used by anyone for free.
- The pro/enterprise version adds extensions to the basic version for advanced usage and requires
  a valid license.

- Install
  - locally
  - with docker / docker compose
  - with k8s / using manifests / using helm / using your own helm chart
- Setup / Configuration
  - database
  - environment

Indices and tables
::::::::::::::::::

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
