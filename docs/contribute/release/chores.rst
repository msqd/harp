Chores
======

Before a new version is released, it's usually a good idea to do some housekeeping.

.. note::

    These are chores, not the gate. Doing all of them does not make a release ready to tag: that
    takes the product owner's recette and the user's sign-off. See :doc:`validation`.

Code review passes
::::::::::::::::::

Before cutting a release, the codebase goes through a sequence of review passes so the
release ships with known, deliberate trade-offs rather than surprises. Each pass lands its
changes in a dedicated, release-scoped branch (kept separate from feature work and the
version bump) so the release diff stays readable, and each pass is reviewed and accepted
before the next one starts.

#. **Simplification review** — quality only: reuse, simplification, efficiency and clarity.
   Run it first on the delta since the previous release (while it is fresh), then across the
   whole codebase. This pass is not a bug hunt; larger refactors it surfaces are recorded as
   follow-ups instead of being forced into the release.

#. **Comprehensive review** — a deeper, multi-dimensional pass over the whole codebase
   (architecture, performance, testing, reliability, maintainability) to catch caveats the
   simplification pass is not meant to find. Actionable, low-risk findings are fixed in the
   release-scoped branch; anything larger or riskier is recorded as a follow-up.

#. **Security review** — a final pass focused on security (input handling, authentication and
   secrets, dependency and supply-chain surface, injection and SSRF vectors) run before the
   cut.

   It is not the first adversarial look a security fix gets. A pull request that fixes a security
   finding is attacked at acceptance, by someone other than its author, with the same hostile
   inputs this review would try. When a guard is bypassed a second time, stop patching it: replace
   it with a rule that refuses the whole class of input, as the proxy path guard did in 0.10 after
   four rounds.

Keep this section up to date as the review process evolves.

Python dependencies (uv)
::::::::::::::::::::::::

Listing outdated dependencies::

    uv tree --outdated --depth 1

Upgrade all locked versions of packages::

    uv lock --upgrade

Or a specific package::

    uv lock --upgrade-package <package>


Frontend Dependencies
:::::::::::::::::::::

.. code-block:: shell-session

    ( cd harp_apps/dashboard/frontend; pnpm list )


To upgrade interactively:

.. code-block:: shell

    (
       cd harp_apps/dashboard/frontend;
       pnpm update --interactive
    )


Run the tests, luke
:::::::::::::::::::

.. code-block:: shell

    uv run make qa

Before you read the result, read :doc:`what-the-gate-does-not-run`. It lists everything this command
does not execute, and why a green run is a weaker statement than it looks.

``tests/test_cookiecutter_integration.py`` scaffolds its projects with ``HARP_SOURCE`` set to the working
tree (see ``harp create project --help``), so it runs before the version exists on PyPI. A failure
there is a real signal.


Run the RFC 9111 compliance suite, on PostgreSQL
::::::::::::::::::::::::::::::::::::::::::::::::

``make qa`` does not run it. It is a separate target, and the release run must name its storage
backend, because the same suite on SQLite and on PostgreSQL are two different measurements.

.. code-block:: shell

    CACHE_TESTS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cachetests \
        uv run make test-e2e-cache

**Run it on PostgreSQL, not the SQLite default.** SQLite does not enforce column widths, and a
40-character ``blobs.id`` reached the 0.10 release candidate because every instrument pointed at it
was pointed at SQLite. The default exists so a contributor can run the suite with nothing installed;
it is not what validates a release.

The target prints the score with its backend and fails on any test that passed in the recorded
baseline and fails twice in a row. It does **not** fail on a lower percentage: see
``docs/adr/0003-cache-compliance-compared-per-test-against-a-pinned-baseline.md`` for why, and
``misc/cache-tests/README.md`` for how to read the report.


README and credits (minor releases)
:::::::::::::::::::::::::::::::::::

The README is the first page most people read. Before each minor release:

* **Credits**: bring People & Credits up to date with every contributor since the last minor
  release, as :doc:`contributors` describes.
* **README**: reread it against the release. Every claim must hold for this version and match the
  docs; every link must resolve; every path it offers into the docs must still lead somewhere
  useful. Regenerate its captures and diagrams if the UI or the architecture changed.

Fix what is wrong in the same release.


Eventually commit the updated dependencies
::::::::::::::::::::::::::::::::::::::::::

.. note::

    These chores touch ``pyproject.toml``, but **not its version field**. The version number and the
    changelog release date are set by the release engineer at cut time, and are the only two things
    in this file that are. See :doc:`python` for why.

.. code-block:: shell

    git add -p pyproject.toml uv.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml

All good ? Let's push that.

.. code-block:: shell

    git commit -m "chore: cleanup and update dependencies"
    git push
