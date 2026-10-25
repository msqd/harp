# explore/audit: decisions from the grill

Decisions taken while grilling explore/audit (2026-10-24, 2026-10-25). Vocabulary lives in
`CONTEXT.md`; this file holds the design choices. Built on explore/auth (actor context, decision 25
there).

1. Vocabulary: one term, Audit Event, plus Actor. The whole set is "the audit". Audit Event is
   distinct from the Transaction Record: never shed, never edited.
2. An audit event is written in the same commit as the action it records, without coupling apps: the
   acting app opens its unit of work, makes its change, then dispatches a domain event of a shared
   type defined in `harp/` that carries the open unit of work. The audit app listens and writes its
   row through it; the commit happens once dispatch returns. A failing audit write raises
   (`adispatch` awaits listeners in turn and re-raises, `harp/event_dispatcher/__init__.py:28-40`),
   rolls back, and fails the action. Apps depend on the event contract only, never on each other.
3. (Superseded by 13.) Actions outside the database (endpoint up/down is in-memory state, cache purge may hit Redis):
   the emitter opens a unit of work for the trace alone and commits an `attempted` event before
   acting, then dispatches a second event with the outcome. Never through the storage worker queue
   that sheds.
4. No critical action passes untraced, without making any app mandatory: every app that performs a
   critical action declares `audit` in its `dependencies` (auth, dashboard, later the cache
   explorer), so audit is loaded whenever such an action can happen. A HARP without them loads no
   audit. The Operator sets retention and log output, not whether actions are traced.
5. No hash chain in the first iteration: append-only in the database, and every event also emitted
   as a structured JSON log line for an external SIEM.
6. Apps stay optional and modular, with no exception: "always loaded" is expressed as declared
   dependencies (`harp/config/applications.py:173-191`). The core (`harp/`) holds contracts only:
   the unit-of-work event type and the actor context type. Apps implement them: auth produces the
   actor, audit listens. Auth and audit are not core: the core has no persistence nor UI.
7. Retention: 365 days by default (`audit.retention_days`), purged by the janitor, separate from the
   60 days of transactions. Longer keeping is the SIEM's job, fed by the log output.
8. Refusals of critical actions are recorded: a 403 on one gives an event of the refused action with
   outcome `denied` and `required_role` in its details. Refused reads are not recorded.
9. Catalogue feedback (2026-10-25): keep signed_in (who, how, when: very important), signed_out,
   sessions_revoked, invitation created/accepted/revoked (including the ones HARP issues itself,
   such as the setup invitation), account created/role_changed/disabled/enabled,
   password_changed, identity linked/unlinked, token created/revoked. Drop setup_link_issued and
   setup_completed (the setup link is an ordinary invitation), basic_users_imported (Basic is
   deprecated and goes soon). sign_in_failed: the user leans to a log, not an audit event.
   proxy.remote.state_changed and http_cache.invalidated: open (manual vs automatic, flood).
10. Boundary: the audit covers the control plane only, i.e. what an account does to HARP (dashboard,
    API, CLI) and the access HARP grants itself (setup invitation, actor = system). The data plane,
    PURGE over HTTP included, belongs to the transaction record; automatic behaviour (breaker,
    liveness, janitor) has no actor and belongs to logs and metrics. Hence: sign_in_failed is a
    structured log line, not an audit event; a manual remote up/down by an Editor and a dashboard
    cache invalidation are audit events; automatic breaker transitions and HTTP PURGE are not.
11. Mechanism (refines decision 2): a two-phase unit of work in the core, on whistle unchanged. The
    acting app runs `async with unit_of_work() as uow: ...; await uow.record(event)`. During the
    transaction, `record` dispatches on a dedicated transactional dispatcher (a second
    `AsyncEventDispatcher` provided by the core container), where only listeners declared
    transactional subscribe, today the audit alone: their writes join the commit and their
    failure rolls the action back. After commit, the same event is dispatched on the main
    dispatcher for everyone else (notifications, metrics, webhooks): a failure there is logged and
    undoes nothing. Ordinary listeners cannot run inside the transaction by construction.
12. Registry, deny by default: each app declares its events as typed classes marked `auditable`
    (control plane, transactional through `uow.record`, imposed: the Operator cannot remove it) or
    `loggable` (dispatched on the main dispatcher, written as a best-effort structured JSON log
    line: automatic breaker transitions, sign_in_failed, HTTP PURGE; the Operator may mute one,
    never add one). An unmarked event reaches neither audit nor log; traffic events
    (`proxy.transaction.*`, `*.filter.*`, `core.request`) are never marked, so flooding is
    impossible by construction. `uow.record` refuses a non-auditable event (programming error).
13. Actions outside the database (manual remote up/down is in-memory state, a dashboard cache
    invalidation may hit Redis) use the same single-row unit of work: write the event, act,
    commit. A failed action rolls back and leaves no row (nothing happened). A commit failing after
    the action restores the previous state when it can (remote state) and otherwise logs a critical
    error; the event's log line still records it. No `attempted` outcome, no pairs of rows.
14. Reading: Admins get an Audit page in the dashboard (filters: actor, action, target, period;
    newest first, paginated) and the API behind it. Every account sees its own sign-ins, sessions,
    tokens and identities under "My account", to spot a device it does not know. Viewers and
    Editors never see others' events. No MCP access to the audit in the first iteration; no export
    in HARP (the log stream feeds the SIEM).
15. Log output: after its commit, each audit event is also written to logger `harp.audit` (same
    fields as the row, `kind: audit`); loggable events go to `harp.events` (`kind: event`). Routing
    uses the existing logging config (`LOGGING_FORMAT=json`, per-logger `LOGGING_<NAME>` levels,
    `harp/_logging.py:41-49`): muting `harp.audit` drops the log copy, never the row. HARP ships
    events nowhere: it writes JSON log lines, and the Operator collects the ones it wants into its
    SIEM with its own collector (Fluent Bit, Vector, Docker log driver, Loki). The operating docs
    show how to filter `logger: harp.audit` / `kind: audit`.
16. The core holds the unit-of-work contract and the transactional dispatcher; it has no
    persistence, so storage provides the unit-of-work implementation (its session factory). Auth,
    dashboard and later the cache explorer use it and declare `audit` in their dependencies.
