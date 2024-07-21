Rules
=====

.. versionadded:: 0.6

.. warning:: Early prototype. The API may change, a lot.

The ``rules`` application implements a powerful way to customize your proxies with specific rules. It works by allowing
to apply a set of user-provided scripts at different stages of the transaction lifecycle.

Scripts are written in python, and are applied conditionally based on patterns matching the transaction's properties.


Reference
:::::::::

.. toctree::
    :maxdepth: 2

    quickstart
    patterns
    lifecycle
    recipes
    Reference </reference/apps/harp_apps.rules>
