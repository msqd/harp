Chores before releasing
=======================

Before a new release is sent to the world, it's usually a good idea to do some housekeeping.


Python dependencies
:::::::::::::::::::

Python dependencies are managed by poetry.

To bump a library:

* identify the library to bump
* (eventually) change the requirement in pyproject.toml
* run `poetry update <library>`
* copy the upgrade for commit message later
* run `make qa`
* all good? Commit the changes with `git commit -m "chore: bump <lib with version>"`

.. code:: shell-session

    vi pyproject.toml
    poetry update ...
    git add -p pyproject.toml poetry.lock
    git commit -m "chore: bump ..."
    make qa


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

    poetry run make qa


Eventually commit the updated dependencies
::::::::::::::::::::::::::::::::::::::::::

.. code-block:: shell

    git add -p pyproject.toml poetry.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml

All good ? Let's push that.

.. code-block:: shell

    git commit -m "chore: cleanup and update dependencies"
    git push
