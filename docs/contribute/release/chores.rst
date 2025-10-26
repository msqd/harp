Chores before releasing
=======================

Before a new version is released, it's usually a good idea to do some housekeeping.

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
