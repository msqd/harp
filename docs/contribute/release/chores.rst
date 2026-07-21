Chores
======

Before a new version is released, it's usually a good idea to do some housekeeping.

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


Eventually commit the updated dependencies
::::::::::::::::::::::::::::::::::::::::::

.. code-block:: shell

    git add -p pyproject.toml uv.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml

All good ? Let's push that.

.. code-block:: shell

    git commit -m "chore: cleanup and update dependencies"
    git push
