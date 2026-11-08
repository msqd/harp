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

The path is a normalised form of the target, never the raw target as sent. The proxy still forwards the target
unchanged: only what rules see is normalised, so that a rule matches what the upstream will act on.

- a leading scheme and authority are removed, so ``http://example.com/admin`` and ``//example.com/admin`` both match
  ``GET /admin``;
- percent-escapes of unreserved characters (letters, digits, ``-``, ``.``, ``_``, ``~``) are decoded, so ``/%61dmin``
  matches ``GET /admin``;
- empty segments are dropped: ``/api//admin`` is matched as ``GET /api/admin``;
- ``;`` parameters are dropped from each segment: ``/admin;x=1/users;id=2`` is matched as ``GET /admin/users``;
- a final slash is kept, once: ``/admin//`` and ``/admin/;x`` are matched as ``GET /admin/``. An ``on_request`` or
  ``on_response`` pattern whose path has no wildcard (``GET /admin``, ``* /admin``) also matches the path with its final
  slash removed, endpoint patterns and ``on_remote_*`` levels excepted, so ``GET /admin`` matches
  ``/admin`` and ``/admin/``, and ``GET /admin/*`` matches ``/admin/`` but not ``/admin``;
- the query string is not part of it, ``GET /users/42?page=2`` is matched as ``GET /users/42``.

An encoded slash, ``%2F`` (any case), stays as sent in that path: ``/a%2Fb`` is matched as ``GET /a%2Fb``. Many
upstreams read it as a slash, so ``on_request`` and ``on_response`` rules are also matched against a second form with
``%2F`` taken as ``/`` (and normalised as above): ``GET /a/b`` matches ``/a%2Fb`` too. A rule runs once per request,
whichever form matched it.

.. admonition:: Writing a deny rule that holds
    :class: warning

    A rule denies what its pattern matches, nothing more. Write the pattern on the normalised path (no ``;``, no
    ``//``) and it holds for the variants above. Known limits, which patterns cannot cover for you:

    - to deny a path and everything under it, write ``GET /admin*`` (it also matches ``/administrator``):
      ``GET /admin/*`` does not match ``/admin`` itself, and ``GET /admin`` only matches that path;
    - double-encoded escapes (``%252F``), a ``%3B`` read as ``;``, ``%00``, ``%5C`` and backslashes, case-insensitive paths and any other
      rewriting specific to your upstream are not normalised;
    - the proxy refuses dot segments (``/./``, ``/../``, encoded or not) on its own, rules do not need to cover them.

    When the upstream is the authority on access, deny there as well: the rules only know the path as the proxy
    receives it.

This is the string matched by ``on_request`` and ``on_response``, and the one the storage markers set by those rules
rely on.

.. versionchanged:: 0.13

    ``on_remote_request`` and ``on_remote_response`` still match the path sent to the remote endpoint, base path and
    query string included (``GET /api/users/42?page=2``, not normalised). A rule that matches only thanks to the query
    string logs a deprecation warning, and remote levels will match the path only in the next release: write the
    pattern as ``GET /api/users/42*`` or ``GET /api/users/*`` to be ready.

.. code-block:: toml

    # on_request: matched as "GET /admin", whatever the target was (/admin?x=1, http://host/admin, /%61dmin).
    [rules."*"."GET /admin"]
    on_request = "request.headers['X-Admin'] = 'yes'"

    # on_remote_request: matched as "GET /api/users/42?page=2" for now, rewrite it to end with a wildcard.
    [rules."*"."GET /api/users/*"]
    on_remote_request = "request.headers['X-Remote'] = 'yes'"

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
