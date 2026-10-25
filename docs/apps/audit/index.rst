Audit
=====

.. tags:: applications

The ``harp_apps.audit`` application keeps the audit events: what an account did to HARP (a change to someone's access, a
manual action on traffic), when, by which means and with what outcome. Each event is written in the same database commit
as the action it records, so there is no action without its event, and no event without its action. If the event cannot
be written, the action fails and nothing is changed.

Audit events are never edited, and never shed under load. The only deletion is the retention.

Loading
:::::::

The audit is not loaded by default, and you do not enable it yourself: the applications that perform critical actions
declare ``audit`` in their dependencies, so it is loaded whenever such an action can happen. A HARP without them loads no
audit. The audit tables exist in the database all the same, empty, as every application's tables do.

If you list your applications by hand, add ``audit`` to the list when an application you enabled requires it, or HARP
refuses to start and tells you so.

Settings
::::::::

``retention_days``
    Age in days after which an event is deleted. Positive integer, default ``365``. The janitor does the sweep, together
    with its own, and independently of the retention of transactions (``janitor.old_after``). The janitor must be
    enabled for events to be purged. Keeping them longer is the job of your SIEM, fed by the log output below.

.. code-block:: yaml

    audit:
      retention_days: 730

What an event holds
:::::::::::::::::::

Table ``audit_events``:

``id``, ``occurred_at``
    Increasing identifier and UTC timestamp.

``action``, ``outcome``
    The name of the action (``auth.account.role_changed``), and its outcome: ``succeeded``, ``failed`` or ``denied``.

``actor_account_id``, ``actor_label``
    The account that acts and its username, copied. Empty when HARP acts on its own. There is no foreign key: an event
    outlives the account.

``actor_via``, ``actor_via_id``, ``actor_client``
    ``session``, ``token``, ``cli`` or ``system``, with the id of the session or token, and the client the account acts
    from when known.

``ip``, ``user_agent``
    Where the request comes from.

``target_type``, ``target_id``, ``target_label``
    What the action is about. The label is copied (the username, the name of a token), so it stays readable once the
    target is deleted.

``details``
    A short JSON, specific to each action. Default-deny: each event class declares the detail fields it may carry
    (``details_fields``), only those are written to the row and the log, and the others are dropped with a warning that
    names them. An event class has no field for a secret (a token creation declares ``prefix`` and ``name``, never the
    token), and a class declaring a field named like one (``password``, ``secret``, ``token``, ``key``...) cannot be
    defined. Fields ending in ``_id``, ``_name``, ``_label``, ``_type`` or ``_prefix`` are fine.
    A declared field holds a scalar (text, number, boolean, null) or a list of them; a dict or a nested structure is
    dropped with a warning. The event author declares which fields are safe and values are not inspected, so a declared
    field must never carry a credential (ids, names, prefixes and scopes only).

Append-only
:::::::::::

Events are never edited: no route nor service updates or deletes a row, and the only deletion is the retention. This is a
guarantee of the code, not of the database. If you want the database to enforce it, with PostgreSQL revoke ``UPDATE`` and
``DELETE`` on ``audit_events`` from the role HARP connects with, and run the retention with a separate role that keeps
``DELETE``.

Log output
::::::::::

Once the commit is done, each event is also written to the ``harp.audit`` logger, with the same fields as the row, the
id of the row, and ``kind: audit``. Collect it into your SIEM with the collector of your choice, filtering on
``logger: harp.audit`` or ``kind: audit`` (use ``LOGGING_FORMAT=json``). Muting the logger drops the copy, never the row.

.. seealso::

    - :ref:`Events » Recording an auditable event <events-unit-of-work>`
