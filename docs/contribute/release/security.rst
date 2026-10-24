Security Release
================

A release that ships fixes for GitHub security advisories. The branching rules are in
:ref:`the Security fixes section of the branching page <branching-security-fixes>`; this page is the order of
operations, from report to publication. Everything before step 6 stays private.

1. Validate each advisory
-------------------------

For every report, before any fix is merged anywhere:

- **Real and reproduced**: reproduce it on the latest release and on ``main``, on ``127.0.0.1``, and keep the
  commands and output.
- **Scope**: first affected version (``git log -S``, ``git tag --contains``), the affected range
  (``<= X.Y.Z``) and the patched versions (one per supported line).
- **Body**: title naming the impact, Summary, Impact (who, preconditions, default or opt-in), Patches,
  Workarounds, Details, PoC, Credits for an outside reporter. CVSS 3.1 vector and CWE.
- A report still in triage is accepted to draft first. Request a CVE from the advisory.

2. Fix in the temporary private fork
------------------------------------

Create the advisory's temporary private fork. One pull request per supported line, ``main`` and the version
lines, each with its tests and its ``security`` changelog fragment. CI does not run there: run the full suite
locally on each head.

A fix that builds on another advisory's fix is stacked on its branch, and merges after it (step 5). Say so in
both forks.

3. Accept
---------

Accept each pull request on its head SHA, mutants included, as for any other. Comments are refused on fork
pull requests: keep the acceptance record privately until publication.

4. Recette
----------

Merge every fork head locally, detached, onto each line, in the release-day order, and run the release
recette on that. Never push those merges.

5. Release day: merge
---------------------

After the recette sign-off:

1. Switch the admin bypass of the *Protected branches* ruleset to *Always*: the advisory page does not count
   as a pull request merge.
2. On each advisory page, **Merge pull requests**, one advisory at a time, stacked fixes last. A refusal for
   conflicts goes back to the fix's author, who merges the base branch into the fork branch, never rebases;
   accept again on the new SHA.
3. Switch the bypass back to *For pull requests only*.
4. Wait for CI on ``main`` and every version line.

6. Release and publish
----------------------

1. Cut the patch releases, then the minor one, per :doc:`python`. Each security entry names its advisory
   (``GHSA-xxxx-xxxx-xxxx``), and the minor release repeats the security entries of the patches shipped
   since the previous minor (see :doc:`changelog`).
2. Once every patched version installs from PyPI, publish each advisory.
3. Remove the forks' remotes and branches, and file the follow-ups held back by the embargo.
