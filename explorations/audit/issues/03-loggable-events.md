# core: loggable events to the `harp.events` logger

**Problem**

Some events matter to operators without being control-plane actions: a breaker opening on its own, a failed sign-in. They belong in the logs, and per-request events must never get there by configuration.

**Acceptance criteria**

- Events marked `loggable`, dispatched on the main dispatcher, are written as one structured line to logger `harp.events` with `kind: event`, best-effort.
- A setting lists `loggable` events to mute; naming an event that is not `loggable` fails configuration validation. There is no way to log an unmarked event (test with `proxy.transaction.started`).
- Routing and format follow the existing logging configuration (`LOGGING_FORMAT`, per-logger levels).

**Out of scope**

Metrics derived from these events.
