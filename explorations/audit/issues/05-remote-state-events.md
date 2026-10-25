# proxy: remote state changes as events, manual ones audited

**Problem**

A remote's state changes by plain attribute assignment (`harp_apps/proxy/settings/remote/__init__.py:194-220`, `harp_apps/proxy/settings/liveness/base.py:49-56`), whether an Editor set it by hand or the breaker did. Nothing records either, and nothing tells them apart.

**Acceptance criteria**

- A manual change through `PUT /api/system/proxy` runs in a unit of work and records the `auditable` event `proxy.remote.state_changed` (endpoint, url, from, to), with the Editor as actor; a refused attempt records `denied`. A commit failing after the change restores the previous state (test).
- A transition made by the breaker or liveness emits the `loggable` event `proxy.remote.state_changed` with no actor; it is never an audit row. Only real transitions emit, not every check (test: repeated failures on a down remote emit once).
- The dashboard declares `audit` in its dependencies.

**Out of scope**

Metrics of transitions; probe internals.
