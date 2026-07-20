# Definition of Ready & Definition of Done

Two short checklists that keep HARP's flow honest: an issue must be **Ready** before work
starts, and a pull request must be **Done** before it merges. Every line is meant to be
checked, not admired. Keep it lightweight; when a line genuinely does not apply, say why.

## Definition of Ready (DoR)

An issue is ready to be picked up when:

- **Why is clear**: the problem and the expected outcome are stated; out of scope is bounded.
- **Shaped as a story**: role, action, result; small enough to ship in one iteration (split if not).
- **Acceptance criteria**: 3 to 5 verifiable criteria, including at least one negative / regression case.
- **Dependencies resolved**: design, API, docs and blocking issues are settled within reach.
- **Approach agreed**: for anything non-trivial, the technical direction is confirmed by a maintainer.
- **Estimated**: coarsely sized.

## Definition of Done (DoD)

A pull request is done when every applicable item is verified. Each PR restates this as a
checklist (see [`.github/pull_request_template.md`](.github/pull_request_template.md)):

- **Automated tests** cover new or changed behaviour. No new tests are expected for codeless changes (documentation, CI / tooling) or for refactors already protected by adequate existing coverage: the code owner judges what is adequate, case by case. No tests written just to tick a box.
- **Tests pass at all times**: the full suite is green in CI on the PR head; nothing merges red.
- **Docs checked**: behaviour or public-interface changes update the docs and the changelog in the same PR.
- **Comprehensive review**: an automated, in-depth review has been run and its findings resolved or explicitly dismissed.
- **Code review approved**: at least one code owner has an approving review on GitHub (marked ready to merge).
- **Manual verification**: begins only once CI is fully green on the PR head, then confirms the behaviour end-to-end; the reviewer decides which manual checks are worth locking in as automated tests.
- **Acceptance criteria met**: every criterion on the issue is satisfied.

Code owners (whose review gates a merge) are listed in
[`.github/CODEOWNERS`](.github/CODEOWNERS).
