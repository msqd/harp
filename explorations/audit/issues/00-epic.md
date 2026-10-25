# Epic: an audit of what accounts do to HARP

**Problem**

Nothing records who changed someone's access, who signed in, or who set a remote down by hand. Once accounts, roles and tokens exist (epic #1527), an Admin cannot answer "who gave Bob the Admin role, and when?", and an account cannot see that an unknown device signed in as it.

**Outcome**

Every control-plane action (sign-ins, access administration, manual actions on traffic, refusals of those actions) leaves an audit event written in the same commit as the action, never shed, never edited, kept 365 days, and copied to the `harp.audit` JSON logger for the Operator's SIEM. Applications stay decoupled: a two-phase unit of work in the core puts the audit write in the action's transaction and runs every other listener after the commit; events are declared `auditable` or `loggable` by the app that emits them, and unmarked events (all traffic events) can reach neither audit nor logs. Admins browse the audit in the dashboard; every account sees its own activity.

Design, vocabulary and decisions, on branch `explore/audit` (branched from `explore/auth`): `CONTEXT.md` (Audit Event, Actor), `explorations/audit/decisions.md`, `explorations/audit/catalogue.html`, ADR-0013.

**Children** (milestone explore/audit, PRs into branch `explore/audit`)

1. core: two-phase unit of work and declared events
2. audit: record auditable events in their action's commit
3. core: loggable events to the `harp.events` logger
4. auth: record its audit events
5. proxy: remote state changes as events, manual ones audited
6. dashboard: the Audit page and "My activity"
7. docs: operating the audit and collecting it into a SIEM

**Out of scope**

Hash chaining (tamper evidence); shipping events to a SIEM from HARP; audit through MCP; cache invalidation events (explore/cache).
