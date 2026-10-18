Patterns and syntax
===================

The rules engine uses rules definition based on 3-levels of pattern matching:

- **endpoint**: the first level allows to filter on which endpoints should match, by endpoint name.
- **request**: the second level allows to filter on the request's fingerprint.
- **stage**: the third level allows to filter on which stage the filter should apply.

Under those three levels, you'll find a list of python code blocks that will be compiled and executed when the
matching events occurs.

.. include:: examples/rules.inc

Matching grammar
::::::::::::::::

Each level is a pattern matched against a value computed from the transaction. The same grammar applies to the three
levels:

- ``*`` matches any sequence of characters, including none, ``/`` and spaces. It can appear anywhere, any number of
  times: ``httpbin-*``, ``GET /users/*``, ``* /health``.
- Every other character is literal, there is no other special character (no ``?``, no regular expression).
- The whole value must match, not a part of it: ``api`` does not match ``api2`` nor ``my-api``.
- Matching is case-sensitive.

Endpoint
--------

The value is the endpoint name, as defined in your configuration.

.. literalinclude:: examples/patterns-endpoint.toml
    :language: toml

Request
-------

The value is the request fingerprint, ``<METHOD> <path>``, for example ``GET /users/42``. The method is upper case
and separated from the path by one space, so you can match on the method (``GET *``), on the path (``* /health``), or
on both (``POST /orders``).

For ``on_request`` and ``on_response``, the path is the one received by the proxy, without query string. For
``on_remote_request`` and ``on_remote_response``, the path is the one sent to the remote endpoint, and it includes the
query string (``GET /users/42?page=2``).

.. literalinclude:: examples/patterns-request.toml
    :language: toml

Stage
-----

The value is the name of the lifecycle event being triggered: ``on_request``, ``on_remote_request``,
``on_remote_response`` or ``on_response`` (see :doc:`lifecycle`). In a rule, the stage is the key of the script, so
a wildcard there can attach one script to several stages.

.. literalinclude:: examples/patterns-stage.toml
    :language: toml

Which rule wins
---------------

None: there is no precedence, a more specific pattern does not override a more general one. Every rule matching the
three levels runs, and a later script sees what the earlier ones did to the request or the response.

Rules are stored as a tree and walked depth first: grouped by endpoint pattern, then by request pattern, then by stage,
each in order of first appearance across all the loaded files. Scripts under the very same keys run in the order they
are written, then in the order the files are loaded.

.. literalinclude:: examples/patterns-order.toml
    :language: toml

On ``GET /x`` for endpoint ``api``, ``X-Trail`` ends up as ``,A,C,B``, not ``,A,B,C``: C is grouped with A under the
``*`` endpoint pattern, before B. For any other endpoint it is ``,A,C``.

If a second file, loaded after the first one, adds a script under the same keys:

.. literalinclude:: examples/patterns-order-more.toml
    :language: toml

the result becomes ``,A,C,E,B``: E joins the existing ``*`` / ``GET *`` group.
