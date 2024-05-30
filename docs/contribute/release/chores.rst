Chores before releasing
=======================

Before a new release is sent to the world, it's usually a good idea to do some housekeeping.


Update and cleanup dependencies
:::::::::::::::::::::::::::::::

Read dependencies list, ensure nothing is outdated
--------------------------------------------------

.. code-block:: shell-session

    $ poetry show --tree --without dev

.. code-block:: shell-session

    $ ( cd harp_apps/dashboard/frontend; pnpm list )


Update dashboard's frontend dependencies
----------------------------------------

.. code-block:: shell-session

    $ (
         cd harp_apps/dashboard/frontend;
         pnpm update --interactive
      )


Update python dependencies
--------------------------

To update all dependencies to their latest compatible version, use the following (requires the poetry-up plugin).
Beware that everything will be updated non interactively, you must review pyproject.toml diff after that.

.. code-block:: shell-session

    $ poetry up
    $ git diff pyproject.toml


Check that all tests are passing (they need background services, for now)
-------------------------------------------------------------------------

.. code-block:: shell-session

    $ docker compose up -d
    $ poetry run make qa


Eventually commit the updated dependencies
------------------------------------------

.. code-block:: shell-session

    $ git add -p pyproject.toml poetry.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml
    $ git commit -m "chore: cleanup and update dependencies"
    $ git push
