.. _storage-redaction:

Redaction
=========

.. versionadded:: 0.13

HARP replaces the value of a credential with the placeholder ``REDACTED`` before anything is written to the
transaction record or to the :doc:`HTTP cache </apps/http_cache/index>`. The database, its backups and the dashboard
never hold the value. The decision is recorded in
`ADR-0009 <https://github.com/msqd/harp/blob/main/docs/adr/0009-credentials-redacted-before-storage-by-rule.md>`_.

What is redacted
::::::::::::::::

By default, the value of four headers: ``Authorization``, ``Proxy-Authorization``, ``Cookie`` and ``Set-Cookie``,
whether they travel on a request or on a response. No query parameter is redacted by default: no parameter name is a
credential across APIs, so you name the ones that are.

Redacted values are replaced in every copy HARP keeps:

- the **request summary** (``GET /oauth/token?client_secret=REDACTED``): the value of each named query parameter, every
  occurrence, the name stays;
- the **headers** of each request and response message: the whole value, every occurrence, the name stays. ``Bearer xyz``
  becomes ``REDACTED``, and a ``Cookie`` or ``Set-Cookie`` value is replaced whole, cookie names included;
- the **headers of the cache entry**, under the conditions below.

Header names match case-insensitively; query parameter names match exactly. The request forwarded to the origin and
the response returned to the caller are never changed: only what is stored.

Choosing what is redacted
:::::::::::::::::::::::::

A :doc:`rule </apps/rules/index>` edits the two sets of its transaction, ``transaction.redaction.headers`` and
``transaction.redaction.query``, with ordinary set operations.

.. code-block:: toml

    # Redact a query parameter on one route.
    [rules."*"."GET /oauth/token"]
    on_request = """
    transaction.redaction.query.add("client_secret")
    """

    # Redact a header specific to one origin.
    [rules."payments"."*"]
    on_request = """
    transaction.redaction.headers.add("X-Api-Key")
    """

    # Opt out: store Authorization in clear for one endpoint.
    [rules."staging-api"."*"]
    on_request = """
    transaction.redaction.headers.discard("Authorization")
    """

``headers`` applies to request and response headers alike. The sets are read when each message is stored, so an
``on_response`` rule can still change what the stored response redacts. ``on_remote_request`` and
``on_remote_response`` scripts cannot: they have no transaction.

The cache
:::::::::

The cache reads back what it stores, so it cannot keep a redacted copy of what it compares or replays. A response is
**not cached at all** when:

- its ``Vary`` names a redacted header (``Vary: Authorization`` or ``Vary: Cookie`` by default);
- its request URL carries a redacted query parameter;
- it carries a redacted response header (``Set-Cookie`` by default).

Any other response is cached with its request headers redacted. Opting a name out of redaction caches these responses
again, and stores them in clear.

A transaction marked ``skip-request-storage`` or ``skip-response-storage`` is not cached either: what an operator keeps
out of storage stays out of every store. See :doc:`markers`.

What is not covered
:::::::::::::::::::

- Only **new traffic** is redacted. Rows and blobs recorded before the upgrade keep the values they were stored with,
  until you delete them.
- **Path segments** and **request and response bodies** are not redacted, nor is the URL HARP logs at debug level or
  sends in notifications. For an endpoint with a secret in its path or body, a rule setting ``skip-request-storage``
  drops the whole request message, summary included.
- A stored ``REDACTED`` is ambiguous for a caller that really sent that string.
