Rules
=====

.. tags:: applications

.. versionadded:: 0.6

.. warning::

    Preview. The API may change, a lot. We chosed to expose a rather low level API, because we think it's easier to go
    up than down, and we have no idea what use cases our users may come with. If your use case is not covered by the
    current API, or hard to implement, please open a discussion thread about it.

The ``rules`` application implements a powerful way to customize your proxies with specific rules. It works by allowing
to apply a set of user-provided scripts at different stages of the transaction lifecycle.

Scripts are written in python, and are applied conditionally based on patterns matching the transaction's properties.

.. toctree::
    :hidden:
    :maxdepth: 2

    Getting Started <quickstart>
    patterns
    lifecycle
    recipes
    commands
    Internals </reference/apps/harp_apps.rules>


Table of Content
::::::::::::::::

.. include:: /apps/rules/_toc.rst
