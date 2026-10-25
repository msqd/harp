Audit
=====

.. tags:: operate, security

The audit answers "who did what to HARP, and when". This page tells you what it records, how long it keeps it, and how to
send it to your SIEM. The application itself is described in :doc:`/apps/audit/index`.

What is recorded
::::::::::::::::

The audit covers the **control plane**: what an account does to HARP, through the dashboard, the API or the command
line, and the access HARP grants itself (an actor of ``system``). It records the action, the actor, the target, the
outcome and where the request came from.

It does not record:

Traffic
    The requests that go through the proxy, ``PURGE`` over HTTP included, belong to the transactions. Nothing in the
    proxy path is ever audited, so no volume of traffic can flood the audit.

Automatic behaviour
    The breaker, the liveness checks, the janitor: nobody acted. They go to the logs and the metrics, and the ones worth
    a line are the loggable events below.

Reads
    Looking at the dashboard, a transaction or the audit itself is not an event. A request refused for lack of a role is:
    it is recorded with the outcome ``denied``.

An action and its event share one database commit. If the event cannot be written, the action fails and nothing
changes. Events are never edited, and never shed under load.

Retention
:::::::::

Events stay in the database for ``audit.retention_days`` days, ``365`` by default, whatever the retention of the
transactions. The janitor deletes the older ones, so it must be enabled.

.. code-block:: yaml

    audit:
      retention_days: 730

HARP does not export the audit. For longer keeping, or to keep it away from the database, collect the log lines below
into your SIEM.

Loggers
:::::::

HARP writes two kinds of structured lines, each from its own logger.

``harp.audit``, ``kind: audit``
    One line per audit event, once its commit is done. It holds the fields of the database row (``id``,
    ``occurred_at``, ``action``, ``outcome``, ``actor_*``, ``ip``, ``user_agent``, ``target_*``, ``details``). If the
    commit fails, there is no row and no line.

``harp.events``, ``kind: event``
    One best-effort line per loggable event: ``event_id``, ``outcome`` and ``details``. There is no actor, as nobody
    acted. You can mute a loggable event with ``core.muted_events``, and the whole logger with ``LOGGING_EVENT_LOG``
    (see :doc:`logging`).

.. code-block:: yaml

    core:
      muted_events:
        - proxy.remote.state_changed

Muting an audit line never removes the row. ``harp.audit`` has no variable of its own: it follows ``LOGGING_HARP``, which
sets the level of every ``harp`` logger.

Collecting the audit
::::::::::::::::::::

Set ``LOGGING_FORMAT=json`` so that each line is one JSON object, written to the standard error of the process. Here is
an audit line (wrapped here for reading):

.. code-block:: json

    {"kind": "audit", "id": 12, "occurred_at": "2026-10-25T10:00:00+00:00", "action": "proxy.remote.state_changed",
     "outcome": "succeeded", "actor_label": "alice", "actor_via": "session", "ip": "203.0.113.7",
     "details": {"endpoint": "api", "from": "up", "to": "down"}, "event": "audit", "logger": "harp.audit",
     "level": "info", "timestamp": "2026-10-25T17:09:30.647416Z"}

Your collector keeps the lines where ``logger`` is ``harp.audit`` (or ``kind`` is ``audit``), and drops the others. Here
is the whole job with `Vector <https://vector.dev>`_, reading the logs of a Docker container named ``harp``. Lines that
are not JSON, such as the startup messages, are dropped too.

.. literalinclude:: examples/vector-harp-audit.toml
    :language: toml

This file was checked with ``vector validate`` and ``vector test`` (Vector 0.43). The collector, the sink and its
authentication are yours to set up. Any collector that can parse JSON and filter on a field does the same job.

Audit events
::::::::::::

The events an account's action writes to the audit. Each event is declared by the application that performs the action.

``proxy.remote.state_changed``
    An Editor set a remote endpoint up, down or checking by hand, with ``PUT /api/system/proxy`` (the dashboard's
    buttons). The target is the remote (``target_type: remote``, its url without credentials as ``target_id``, the
    proxy endpoint's name as ``target_label``). Details: ``endpoint``, ``url``, ``from`` and ``to`` (``up``, ``down`` or
    ``checking``), and ``required_role`` when refused. Outcomes: ``succeeded``; ``denied`` for an account below Editor,
    with the state left alone. Every refused request writes one ``denied`` row, and there is no rate limit yet. The state
    change and the event share one commit: if the commit fails, the endpoint gets its previous state back.

Loggable events
:::::::::::::::

The events written to ``harp.events``, with no actor and no row.

``proxy.remote.state_changed``
    The breaker or the liveness changed the state of a remote endpoint on its own. Written once per real transition: a
    remote that stays down emits nothing more. Details: ``endpoint``, ``url``, ``from`` and ``to`` (``up``, ``down`` or
    ``checking``). A change by an Editor is the audit event of the same name above.

A test checks these two catalogues against the event classes the applications declare, so an event cannot be added or
removed without this page following.
