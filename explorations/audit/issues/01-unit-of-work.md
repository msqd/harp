# core: two-phase unit of work and declared events

**Problem**

An action and the record of it cannot share a commit today: every listener of the main dispatcher runs wherever the event is dispatched, so putting the audit write in the action's transaction would also put every other listener there, and a failing webhook would cancel a change of role. ADR-0012 (branch `explore/audit`) decides a two-phase unit of work.

**Acceptance criteria**

- The core (`harp/`) defines event classes marked `auditable` or `loggable`, and a unit-of-work contract: `async with unit_of_work() as uow: ...; await uow.record(event)`.
- The core container provides a transactional dispatcher, a second `AsyncEventDispatcher`, distinct from the main one. Only listeners registered as transactional attach to it.
- `uow.record` dispatches on the transactional dispatcher inside the transaction; a listener failure rolls back the whole unit of work and fails the action (test). After the commit, the same event is dispatched on the main dispatcher; a listener failure there is logged and the commit stands (test). An ordinary listener never runs before the commit (test).
- `uow.record` refuses an event not marked `auditable` (test).
- Storage provides the implementation on its session factory; the core has no persistence.
- An action outside the database writes, acts, then commits; a failing action leaves nothing; a commit failing after the action calls the action's compensation when it has one, else logs a critical error (tests with a fake action).

**Out of scope**

Any concrete event, table or listener (later children).
