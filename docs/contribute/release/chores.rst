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

Before you read the result, read :doc:`what-the-gate-does-not-run`. It lists everything this command
does not execute, and why a green run is a weaker statement than it looks.

.. important::

    **Expect failures in** ``tests/test_cookiecutter_integration.py`` **before the version is
    published, and do not stop the cut for them** (24 of them at the 0.10 cut).

    The project template pins ``harp-proxy>=X.Y.Z``, and PEP 440 excludes pre-releases from that
    specifier. So while only ``X.Y.Z-alphaN`` or ``X.Y.Z-rcN`` exist on PyPI, ``uv sync`` inside a
    generated project cannot resolve and reports ``No solution found when resolving dependencies``.
    They pass again on their own once ``X.Y.Z`` is published.

    CI never shows this, because it runs ``-m 'not subprocess'`` and these tests are marked
    ``subprocess``. ``make qa`` does not filter, so the release manager is the person most likely to
    meet it, at the exact moment they are deciding whether something is wrong.

    Any failure **outside** that file is a real signal. Check the file names before concluding this
    is what you are looking at.

    `#875 <https://github.com/msqd/harp/issues/875>`_ fixes the template pin and removes this caveat.


Eventually commit the updated dependencies
::::::::::::::::::::::::::::::::::::::::::

.. code-block:: shell

    git add -p pyproject.toml uv.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml

All good ? Let's push that.

.. code-block:: shell

    git commit -m "chore: cleanup and update dependencies"
    git push
