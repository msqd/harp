# ADR-0009: Credentials are redacted before storage, by rule, and credential headers are redacted by default

- **Status**: accepted, not yet implemented
- **Date**: 2026-10-24
- **Decided in**: [#971](https://github.com/msqd/harp/issues/971), [#1139](https://github.com/msqd/harp/issues/1139)

**This decision applies from 0.13 and is not implemented in 0.12.** Up to 0.12, every header value and
every query parameter is stored in clear. [#1140](https://github.com/msqd/harp/issues/1140) implements it.
Line references below are to `main` when this record was written.

HARP replaces the value of a credential with the placeholder `REDACTED` before anything is written to the
transaction record or the cache. Which values are credentials is a set of header names and query parameter
names, held on the transaction and edited by rules. With no rule touching it, the set holds the four
credential headers, `Authorization`, `Proxy-Authorization`, `Cookie` and `Set-Cookie`, and no query
parameter. A rule adds names to it, or removes them to opt out. Nothing already stored is rewritten.

## What is redacted, and where

Values are redacted in every copy HARP keeps:

- **The request summary.** It is built from the method, path and re-encoded query string
  (`harp/http/serializers.py:50-57`) and stored as a column of the message row
  (`harp_apps/storage/worker.py:166-171`). The value of each named query parameter becomes `REDACTED`,
  every occurrence when the parameter repeats. The parameter name stays.
- **The headers blob of each message**, request and response alike. It is one `Name: value` line per
  header (`harp/http/serializers.py:27-29`), stored at `harp_apps/storage/worker.py:182-185`. The whole
  value of each named header becomes `REDACTED`, every occurrence. The header name stays. `Bearer xyz`
  becomes `REDACTED`, not `Bearer REDACTED`; a `Cookie` or `Set-Cookie` value is replaced whole, cookie
  names included.
- **The cache's stored entry.** Its request headers blob (`harp_apps/http_cache/adapters.py:203-205`) and
  its response headers blob (`harp_apps/http_cache/adapters.py:237-245`) follow the same rule, under the
  conditions of [The cache](#the-cache) below.

Header names match case-insensitively, whatever case the rule writes them in, because HTTP field names
are case-insensitive. Query parameter names match exactly, case included.

Redaction happens where a message is serialized for storage, never on the message itself. The request
forwarded upstream and the response returned to the caller are unchanged. This matters because a rule's
script receives the live request object (`harp_apps/proxy/events.py:62-71`): redacting it in place would
send `REDACTED` to the origin.

Not covered by this decision, and left for later: path segments, request and response bodies, and the
URL HARP sends outside storage (the debug log line at `harp_apps/proxy/controllers.py:223-227`, the
notification payload at `harp_apps/notifications/subscriber.py:45-47`). The documentation says so in
those words. Until they are covered, the answer for an endpoint with a secret in its path or body is a
rule setting `skip-request-storage`, which drops the whole request message, summary included
(`harp_apps/storage/worker.py:145-157`).

## The default

With no rule configured, the set holds `authorization`, `proxy-authorization`, `cookie` and `set-cookie`,
and no query parameter. [#1139](https://github.com/msqd/harp/issues/1139) ruled on `Authorization` and
`Cookie`; [#1140](https://github.com/msqd/harp/issues/1140) widened the default to their proxy and
response counterparts, which carry the same kind of value. There is no default list of query parameters:
no parameter name means a credential across APIs, and guessing (`token`, `key`) would hide ordinary values
from operators.

This is [ADR-0001](./0001-compliant-by-default-operator-may-override.md) applied: the safe reading by
default, and an override for the operator who needs the value, typically while debugging an
authentication problem against an origin.

## The rule syntax

Redaction is configured in the rules application, which already governs what is recorded through
transaction markers (`harp_apps/rules/examples/storage-markers.toml`). The transaction carries a
`redaction` attribute with two sets, `headers` and `query`, pre-filled with the default. A rule edits them
with ordinary set operations:

```toml
# Redact a query parameter on one route.
[rules."*"."GET /oauth/token"]
on_request = """
transaction.redaction.query.add("client_secret")
"""

# Redact a header specific to one origin.
[rules."payments"."*"]
on_request = """
transaction.redaction.headers.add("X-Api-Key")
"""

# Opt out: store Authorization in clear for one endpoint.
[rules."staging-api"."*"]
on_request = """
transaction.redaction.headers.discard("Authorization")
"""
```

Header names in a rule are normalised to lower case, so `discard("Authorization")` removes the default
`authorization`. `headers` applies to request and response headers alike: there is one set, not one per
direction, because the default list already spans both and a name that is a secret one way is a secret
the other.

The set is read when each message is stored. The request message is dispatched for storage after the
`on_request` rules have run (`harp_apps/proxy/controllers.py:488-500`), and the response message after the
`on_response` rules (`harp_apps/proxy/controllers.py:234`, then `harp_apps/proxy/controllers.py:261` and
`harp_apps/proxy/controllers.py:430`). An `on_response` rule can therefore still change what the stored
response redacts. `on_remote_request` and `on_remote_response` scripts cannot: their context holds no
transaction (`harp_apps/http_client/events.py:53-61`).

The cache works at the HTTP client layer, below the transaction. The set, as it stands once `on_request`
has run, travels with the outgoing request in its `harp` extension
(`harp_apps/proxy/adapters.py:99-105`), and the cache applies that one. A request the HTTP client sends
outside a proxied transaction gets the default set.

## The placeholder

The stored value is the literal string `REDACTED`, in the summary and in the headers blobs alike. The
dashboard shows it as it shows any value (`harp_apps/dashboard/frontend/src/Pages/Transactions/Components/MessageHeaders.tsx:33-47`),
so a redacted header is visibly there and visibly redacted, not absent. An absent header still means the
headers were skipped by marker or shed under pressure, which keeps the distinction
[ADR-0002](./0002-caller-no-store-suppresses-payload-recording.md) asks for: a reader can tell a
deliberate redaction from a loss.

The word is chosen for the two places it has to survive:

- **URL encoding.** The summary re-encodes the query string with `urlencode`
  (`harp/http/serializers.py:52`), which percent-encodes everything outside letters, digits and `_.-~`.
  The `***` the configuration dump already masks secrets with (`harp/config/asdict.py:11`) would be stored
  as `%2A%2A%2A`, and `[redacted]` as `%5Bredacted%5D`.
- **The dashboard's summary parser**, which splits the summary on spaces
  (`harp_apps/dashboard/frontend/src/Pages/Transactions/Components/MessageSummary.tsx:36`). A placeholder
  with a space would cut the URL short.

No frontend change is needed for the first slice. A styled rendering of the placeholder may come later; it
does not change what is stored.

## The cache

The cache is a store like the transaction record, so it keeps a redacted copy or nothing. Unlike the
record, it reads its copy back to answer requests, so a redacted value is only safe to store where the
cache never compares or replays it. hishel 1.1.9 compares the stored request's URL to the presented one
as a whole (`hishel/_core/_spec.py:1291`), compares the stored request's value of each header named by
`Vary` to the presented one (`hishel/_core/_spec.py:244`), and replays the stored response headers on a
hit.

Hence three cases where the response is **not stored in the cache** at all:

- **Its `Vary` names a header in the set.** A stored `Authorization: REDACTED` would match no real caller,
  and would match a caller who sends the literal placeholder, handing it a response selected for someone
  else's credential. This is the case [#1140](https://github.com/msqd/harp/issues/1140) ruled on.
- **Its request URL carries a query parameter in the set.** The stored URL is compared whole, so a
  redacted one never matches again: storing it costs a blob and serves nothing, and storing it in clear
  defeats the redaction. *For the cache, see ADR-0014 ("As implemented"): this case changed there.*
- **It carries a response header in the set**, `Set-Cookie` by default. Replaying `Set-Cookie: REDACTED`
  breaks the client; replaying the real value hands one caller's session to the next.

Otherwise the entry is stored with its request headers redacted, which is safe because the cache reads
them only for `Vary`. That includes the `Authorization` HTTP Basic header HARP adds for endpoint
credentials, which is added to the outgoing request only and so never reached the transaction record
(`harp_apps/proxy/adapters.py:80-84`), but did reach the cache.

An operator who opts a name out of the set gets these responses cached again, and stored in clear.

What an operator keeps out of storage stays out of every store. A transaction carrying `skip-request-storage` or
`skip-response-storage` has its response never stored by the cache, which until now ignored these markers. The markers
travel with the outgoing request in its `harp` extension, like the set, as they stand once `on_request` has run.
`skip-storage` is not one of them: the storage worker also sets it itself under pressure, and load must not switch the
cache off. The header and body markers are not honoured either, since the cache stores no body of its own to omit
and its request headers are already redacted.

## Existing data

Nothing already stored is rewritten. Rows and blobs recorded before the upgrade keep the values they were
stored with, until the operator deletes them. Rewriting would mean a migration that reads and rewrites
every headers blob, under a rule set that may not be the one in force when the traffic passed, and the
cache entries expire on their own. The documentation states that redaction applies to new traffic only.

## Rejected

**Redacting at display.** The database, its backups and anything with access to the storage API still hold
the value; the dashboard is one reader among several. [#971](https://github.com/msqd/harp/issues/971)
decided that the database and its backups never hold the value, and only redaction before storage does
that.

**Markers carrying the name** (`redact-query:client_secret`). Markers are the vocabulary for decisions
about a transaction (`CONTEXT.md`), but they are a flat set of strings persisted comma-joined
(`harp/models/transactions.py:9-11`, `harp/models/transactions.py:79`). A parameterised marker needs
parsing, and the opt-out needs a negative form (`keep-header:authorization`). Two sets with `add` and
`discard` say the same thing without a grammar.

**A storage setting listing names** (`storage.redact.headers`). Global only: it cannot say that
`client_secret` is a credential on `/oauth/token` and an ordinary value elsewhere. A rule matching `*` on
both levels gives the global case anyway, and the rules application is where
[#971](https://github.com/msqd/harp/issues/971) placed recording decisions.

**A filter chain in blob storage** ([#74](https://github.com/msqd/harp/issues/74), closed). It would sit
too low: blob storage receives bytes and a content type (`harp/models/blobs.py:37`) and knows neither the
transaction nor its rules, and the request summary is a message column rather than a blob
(`harp_apps/storage/worker.py:169`), so it would never see the query string. Redaction belongs in the
serializer, which has the message, the transaction and its set.

**Relying on the `skip-*-storage` markers.** `skip-request-headers-storage` drops every header to hide one,
and leaves the query string in the summary. `docs/apps/storage/markers.rst:76` presents it as the answer
for sensitive authentication headers, and the cache does not honour it. That page is corrected with
[#1140](https://github.com/msqd/harp/issues/1140).

## Consequences

**Caching changes by default.** Responses with `Set-Cookie`, or with `Vary: Authorization` or
`Vary: Cookie`, are no longer cached unless the operator opts the header out of redaction. A response to a
URL with a redacted query parameter is not cached either (until #1594, see above).

**A stored `REDACTED` is ambiguous in one case**: a caller that really sent the string `REDACTED`. That is
accepted; a marker recording that redaction happened can be added if it ever matters.

**Searching the dashboard for a credential no longer finds it** in new traffic. That is the point, and it
also means a support question of the form "which calls used this key" has no answer from the record.
