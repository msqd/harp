Applications
============

Overview
::::::::

Harp consists of a core library and a set of applications that provides features (including most of the core features).

To allow extensions to do basically anything, Harp uses the following components:

- a dependency injection container (provided by `rodi <https://www.neoteroi.dev/blacksheep/dependency-injection/>`_).
- an event dispatcher (provided by `whistle <https://python-whistle.github.io/>`_).
- an protocol to register applications as plug-and-play extensions to harp.

For now, look at the source of core applications.

Concepts
::::::::

.. toctree::
    :maxdepth: 2

    dependency-injection
    event-dispatcher
    application-protocol

Guides
::::::

.. toctree::
    :maxdepth: 2

    creating
    structure/index
    settings
    using
    testing
    faq
