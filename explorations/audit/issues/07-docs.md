# docs: operating the audit and collecting it into a SIEM

**Problem**

Operators need to know what is recorded, how long it is kept, and how to get it into their SIEM.

**Acceptance criteria**

- An operating page: what the audit records and what it does not (traffic, automatic behaviour, reads), retention and its setting, the `harp.audit` and `harp.events` loggers.
- How to collect: `LOGGING_FORMAT=json`, filtering on `logger: harp.audit` / `kind: audit`, with one example for a common collector (Vector or Fluent Bit).
- The catalogue of audit events and loggable events, generated from the declared event classes or checked against them by a test.

**Out of scope**

Any collector configuration beyond the example.
