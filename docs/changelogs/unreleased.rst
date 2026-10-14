Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- RFC 9111 compliance is now measured and guarded: ``make test-e2e-cache`` runs the cache-tests suite,
  prints the score with the storage backend it was measured on, and fails when a test that passed in
  the recorded baseline fails twice in a row. Baselines are recorded from three runs, so a test that
  flaps while being recorded cannot later raise a false alarm, and a test HARP failed to proxy is
  reported as unobserved rather than counted as a compliance failure.
  ``make test-e2e-cache-baseline REASON='...'`` moves the baseline deliberately. See
  ``docs/adr/0003-cache-compliance-compared-per-test-against-a-pinned-baseline.md``.

Changed
:::::::

Fixed
:::::

- ``make test-e2e-cache`` no longer reports success whatever happens. It could not run at all against a
  working copy, because the committed configuration pointed at a database nothing creates, and every
  guard around that failure was unable to report it.
- ``make test-e2e-cache`` no longer exits 2 on a run where HARP logged no proxy error.

Security
::::::::

- Upgraded dependencies with open advisories: anyio 4.14.2, aiohttp 3.14.5, h2 4.4.1, hpack 4.2.0 and
  cryptography 50.0.2 (``mysql`` extra). The ``aiohttp`` and ``cryptography`` ranges are widened accordingly.
- ``multidict`` range widened to ``>=6.9.1,<7`` (GHSA-54p9-h82j-f925); shipped images no longer stay on 6.7.x.
- Proxy path guard: percent-encoded dot segments (``%2e``), encoded slashes (``%2f``) and backslashes can no longer escape the endpoint base path (400); the raw path is still forwarded unchanged.
- Proxy path guard: encoded ``%3f`` and ``%23`` can no longer hide a base path escape (400), and encoded ``%3A``/``%2F`` in a segment no longer get a legitimate request refused.
- Proxy path guard: a space or control byte in a request path (reachable over HTTP/2) answers 400 instead of escaping the endpoint base path; containment is now decided on the forwarded URL, which is the base path followed by the raw request path (a ``:`` in the first segment is no longer read as a scheme).
- Proxy path guard: any ``.`` or ``..`` segment in a request path answers 400, under ``/``, ``\``, ``%2f`` or ``%5c`` and with literal or ``%2e`` dots (``/a%2fb/../..`` escaped the base path); a path the proxy cannot parse (``//[x/``) answers 400 instead of an error.

Removed
:::::::

- ``misc/cache-tests/open-results.sh``. It served the suite's own HTML viewer, which reads a registry
  of implementations inside the submodule that HARP is not in, so it could never show HARP's results.
