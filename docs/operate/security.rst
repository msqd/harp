.. _operate-security:

Security and hardening
======================

.. versionadded:: 0.13

What HARP exposes, what it records and what to restrict, for an instance in front of production traffic. This page
summarises and links: each topic has its own page, which stays the reference.

HARP sits on the path of your API calls, so it sees and records what they carry, and it trusts whoever writes its
configuration and its :doc:`rules </apps/rules/index>`. It does not terminate TLS and does not decide who may call
your endpoints: put it behind infrastructure that does.

Checklist
:::::::::

- Keep the dashboard login (the default), or bind it with ``dashboard.host: 127.0.0.1``:
  :ref:`operate-security-dashboard`.
- Use PostgreSQL, not SQLite, and read the startup warnings: :ref:`operate-security-dev-settings`.
- Firewall every port you do not publish on purpose, ``/healthz`` and ``metrics_port`` included:
  :ref:`operate-security-ports`.
- Name the query parameters that carry secrets: :ref:`operate-security-recorded`.
- Set ``proxy.trusted_proxies`` if a load balancer is in front: :ref:`operate-security-callers`.
- Pass secrets by environment variable, never on the command line: :ref:`operate-security-secrets`.
- Mind the access log: :ref:`operate-security-logs`.
- Do not set ``HARP_DEBUG``: :ref:`operate-security-errors`.
- Only load rules you wrote: :ref:`operate-security-rules`.


.. _operate-security-ports:

Ports and exposure
::::::::::::::::::

Every port HARP opens (each ``proxy.endpoints[].port``, ``dashboard.port`` and ``dashboard.metrics_port``) binds all
interfaces (``[::]``), so that a published Docker port works. Only ``dashboard.host`` narrows the dashboard port, see
:ref:`operate-security-dashboard`. For the others, restrict at the network level: a firewall or security group, a
Kubernetes ``NetworkPolicy``, or, with Docker, publish only the ports you need, on loopback if they are for the host
(``-p 127.0.0.1:9100:9100``). See :doc:`runtime`.

``/healthz`` answers ``200`` on every port, without authentication, and is not configurable. It reveals only that HARP
runs, and it is what the Docker health check calls.

.. list-table::
    :header-rows: 1
    :widths: 30 25 45

    * - Port
      - Authentication
      - Notes
    * - Endpoint ports (:doc:`proxy </apps/proxy/index>`)
      - None
      - HARP forwards what it receives. Whatever secures your upstream (API keys, mTLS) is the caller's concern.
    * - ``dashboard.port`` (4080)
      - Login by default
      - Also serves ``/metrics``, under the login.
    * - ``dashboard.metrics_port``
      - None, by design
      - Off by default. Serves only ``/metrics`` and ignores ``dashboard.host``.


.. _operate-security-dashboard:

Dashboard
:::::::::

The :doc:`dashboard </apps/dashboard/index>` shows everything that goes through the proxy: reaching it is reaching
your traffic.

- **A login is required by default.** Without ``dashboard.auth``, HARP generates a password for the ``admin`` user at
  each start and logs it once. Set your own users with ``dashboard.auth`` (basic authentication, passwords kept as
  hashes). See the authentication section of :doc:`/apps/dashboard/index`.
- ``dashboard.auth.type: none`` serves the dashboard to anyone who can reach the port. Keep it for a workstation:
  HARP warns about it at every start.
- ``dashboard.host`` sets the address the dashboard listens on. It defaults to ``[::]``; ``127.0.0.1`` serves it on
  loopback only (reach it through an SSH tunnel or a reverse proxy on the host).
- Dashboard responses carry ``X-Content-Type-Options``, ``X-Frame-Options`` and a ``Content-Security-Policy``, and
  captured message bodies are served as sandboxed attachments. Responses also send ``Referrer-Policy: same-origin``.
  See the security headers section of :doc:`/apps/dashboard/index`.
- **Writes are guarded against cross-site requests.** A ``PUT``, ``POST`` or ``DELETE`` on the dashboard is refused
  with ``403`` when the browser flags it cross-site (``Sec-Fetch-Site``) or its ``Origin`` is not the dashboard's, and
  with ``415`` unless it sends ``Content-Type: application/json``. Scripts calling the API must send that content type.

The dashboard speaks plain HTTP and sends the login with every request: terminate TLS in front of it
(:ref:`operate-security-tls`).


.. _operate-security-dev-settings:

Development-only settings
:::::::::::::::::::::::::

At startup HARP logs a ``WARNING`` for every setting that is fine on a laptop and unsafe in production: SQLite as
``storage.url``, ``dashboard.auth.type: none`` and ``HARP_DEBUG``. Treat such a warning in a production log as a defect
of the deployment.


.. _operate-security-recorded:

What is recorded
::::::::::::::::

The :doc:`storage </apps/storage/index>` application records every transaction: request and response summaries,
headers and bodies (up to ``proxy.max_recorded_body_size``). They are shown in the dashboard and kept in the database,
its backups and the :doc:`HTTP cache </apps/http_cache/index>`.

- **Credentials in headers are redacted before storage**: ``Authorization``, ``Proxy-Authorization``, ``Cookie`` and
  ``Set-Cookie``, also in the cache. The request sent upstream is untouched. **Query parameters are not redacted
  unless you name them**, and neither are paths and bodies. Rules choose what is redacted: see
  :doc:`/apps/storage/redaction`, and
  `ADR-0009 <https://github.com/msqd/harp/blob/main/docs/adr/0009-credentials-redacted-before-storage-by-rule.md>`_
  for the reasoning. Only new traffic is redacted: purge what older versions recorded.
- To keep the headers or bodies of an endpoint out of storage, a rule sets a marker (``skip-request-storage`` and
  friends): see :doc:`/apps/storage/markers`.
- **Client tags** (``x-harp-*`` request headers) are set by the caller, without authentication. ``proxy.tags`` bounds
  them (20 tags, names up to 64 characters, values up to 256, by default); strip them at your gateway for untrusted
  callers. See :ref:`proxy-client-tags`.
- **Notifications** carry the URL of the remote request without its query string. See
  :doc:`/apps/notifications/index`.
- **The access log** is another record, see :ref:`operate-security-logs`.

Protect the database like the traffic it holds: restrict access to PostgreSQL, encrypt its volumes and backups, and
let the :doc:`janitor </apps/janitor/index>` delete old transactions (60 days by default).


.. _operate-security-logs:

Logs
::::

HARP's own logs avoid secrets: the generated dashboard password is shown once, and :doc:`Sentry
</apps/contrib/sentry/index>` events never include the command line or local variables. Still:

- **The server access log** (logger ``hypercorn.access``, ``INFO`` by default, set by ``LOGGING_HTTP``) writes the
  request line with its full target, query string included, plus the ``Referer`` and ``User-Agent`` headers, for every
  request on every port. Redaction does not cover it. Raise ``LOGGING_HTTP`` to ``WARNING`` to silence it, or keep the
  log where you keep secrets. See :doc:`logging`.
- At ``DEBUG`` level HARP logs more, request URLs included: do not run production at ``DEBUG``.
- ``LOGGING_SQL`` logs the SQL statements, which can carry recorded data.


.. _operate-security-secrets:

Secrets in configuration
::::::::::::::::::::::::

Settings that hold secrets (``storage.url`` with its database password, the notification webhooks) are better out of
files you commit. Pass them as ``HARP_*`` environment variables (``HARP_STORAGE__URL``) fed by your secret store or a
protected file, not with ``--set``, which shows in the process list and in shell history. See
:doc:`configure/index`.


.. _operate-security-callers:

Callers and request handling
::::::::::::::::::::::::::::

- **Client address.** HARP strips the ``X-Forwarded-For``, ``Forwarded`` and ``X-Real-IP`` headers a client sends and
  appends the peer address upstream. Behind a load balancer, list its ranges in ``proxy.trusted_proxies`` (empty by
  default), or the upstream sees the load balancer as the client. List only proxies you operate. See
  :ref:`proxy-forwarding-headers`.
- **Request framing.** A request carrying both ``Content-Length`` and ``Transfer-Encoding`` is refused with ``400`` and
  the connection is closed, before anything goes upstream.
- **Slow clients.** A client silent for longer than ``proxy.client_read_timeout``, or uploading under
  ``proxy.min_request_body_rate``, gets ``408`` and its request is not forwarded. See
  :doc:`/apps/proxy/index`.
- **Paths.** A path that could leave the subtree of the endpoint URL (dot segments in any encoding, control bytes)
  gets ``400`` and nothing is sent upstream. See the path guard in :doc:`/apps/proxy/index`.


.. _operate-security-metrics:

Metrics
:::::::

Prometheus metrics are served on ``/metrics`` on the dashboard port, under the dashboard login.
``dashboard.metrics_port`` serves them on a dedicated port **without authentication**: leave it unset, or restrict the
port outside HARP. The proxy ports never answer a metrics path: ``/.prometheus/metrics`` is proxied upstream like any other path. See :doc:`prometheus`.


.. _operate-security-errors:

Errors and debug mode
:::::::::::::::::::::

JSON error responses carry the error name and status, and the traceback goes to the log. With ``HARP_DEBUG`` they
include the traceback, values and file paths: never set it in production. See :ref:`configure-debug-mode`.


.. _operate-security-rules:

Rules
:::::

:doc:`Rules </apps/rules/index>` are Python scripts that run inside the proxy process, with its privileges. They are
no sandbox: load only rules written by people allowed to administer the proxy. A failing script does not take the proxy
down: ``on_request`` fails closed (the client gets ``500`` and the request is not forwarded), the other events fail
open, and a script over its ``time_budget`` is abandoned. See :doc:`/apps/rules/execution`.


.. _operate-security-tls:

TLS
:::

HARP serves plain HTTP on all its ports. Terminate TLS in front of it (load balancer, ingress, sidecar) for the proxy
ports and the dashboard, and use ``https`` URLs for the endpoints' upstreams.
