# ADR-0012: A critical action and its audit event share one commit, through a two-phase unit of work

- **Status**: proposed
- **Date**: 2026-10-25
- **Decided in**: [explore/audit](https://github.com/msqd/harp/milestone/25)

**Proposed on the explore/audit exploration branch; nothing of it is implemented.** Line references are
to `main` when this record was written.

An action on HARP's control plane (a change to someone's access, a manual action on traffic) and the
audit event that records it are written in the same database commit, without the acting application
knowing that an audit exists. The core provides a unit of work in two phases, on the existing `whistle`
dispatcher, and every application declares which of its events may be recorded at all.

## The two phases

The acting application runs its change inside a unit of work and hands it the event:

```python
async with unit_of_work() as uow:
    ...  # the change
    await uow.record(RoleChanged(actor=..., account=..., before="viewer", after="editor"))
```

1. **Inside the transaction**, `record` dispatches the event on a **transactional dispatcher**, a
   second `AsyncEventDispatcher` provided by the core container, distinct from the main one. Only
   listeners declared transactional subscribe to it; today that is the audit application alone. Its
   row joins the commit. `adispatch` awaits each listener in turn and re-raises
   (`harp/event_dispatcher/__init__.py:28-40`), so a failed audit write rolls the action back.
2. **After the commit**, the same event is dispatched on the main dispatcher, for every other
   listener: notifications, metrics, webhooks. A failure there is logged and undoes nothing.

An ordinary listener cannot run inside the transaction, because it is never attached to the
transactional dispatcher. A slow webhook can neither hold a transaction open nor cancel a change of
role.

An action outside the database (a remote set up or down by hand is in-memory state, a cache
invalidation may hit Redis) uses the same unit of work: write the event, act, commit. A failed action
rolls back and leaves no row. A commit failing after the action restores the previous state when it
can, and otherwise logs a critical error; the event's log line still records it.

The core has no persistence: it holds the contract and the transactional dispatcher, and storage
provides the implementation, on its session factory.

## Declared events, denied by default

Each application declares its events as typed classes, with one of two marks:

- **auditable**: a control-plane action, recorded through `uow.record`. The mark belongs to the code;
  no setting removes it. `uow.record` refuses an event without it.
- **loggable**: something worth a structured log line but not an audit row, such as a breaker opening
  on its own or a failed sign-in. Dispatched on the main dispatcher; the Operator may mute one.

An unmarked event reaches neither the audit nor the event log. Traffic events
(`proxy.transaction.*`, `*.filter.*`, `core.request`) are never marked, so a configuration cannot flood
either with per-request events, and no deny list is needed.

## Rejected

- **Call the audit service directly.** Simple, but every acting application depends on the audit
  application.
- **Listen on the main dispatcher only.** Decoupled, but nothing guarantees the row is written, and
  every listener of the event would run inside the transaction to keep the guarantee.
- **One dispatcher, two event ids (`<id>:pending` then `<id>`).** Simpler, but nothing stops an
  ordinary listener from subscribing to the pending phase.
- **A transactional outbox.** Decoupled and guaranteed, at the price of a table, a background
  consumer and a delay before the event is readable; actions outside the database gain nothing.
- **An Operator-chosen list of events to record.** Flexible, and the way per-request events get
  logged by mistake.
