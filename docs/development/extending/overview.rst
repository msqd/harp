Overview
::::::::

Harp consists of a core library and a set of extensions that provides features over the core.

A lot of builtin features are provided by extensions, and you can extend the core using the very same API used to
implement core features.

To allow extensions to do basically anything, Harp provides the following components:

- a dependency injection container (provided by `rodi <https://www.neoteroi.dev/blacksheep/dependency-injection/>`_).
- an event dispatcher (provided by `whistle <https://python-whistle.github.io/>`_).
- an protocol to register packages as a plugable extension.
