Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

- RFC 9111 compliance is now measured and guarded: ``make test-e2e-cache`` runs the cache-tests suite,
  prints the score with the storage backend it was measured on, and fails when a test that passed in
  the recorded baseline fails twice in a row. ``make test-e2e-cache-baseline REASON='...'`` moves the
  baseline deliberately. See ``docs/adr/0003-cache-compliance-compared-per-test-against-a-pinned-baseline.md``.

Changed
:::::::

Fixed
:::::

- ``make test-e2e-cache`` no longer reports success whatever happens. It could not run at all against a
  working copy, because the committed configuration pointed at a database nothing creates, and every
  guard around that failure was unable to report it.

Security
::::::::

Removed
:::::::

- ``misc/cache-tests/open-results.sh``. It served the suite's own HTML viewer, which reads a registry
  of implementations inside the submodule that HARP is not in, so it could never show HARP's results.
