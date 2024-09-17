Chores before releasing
=======================

Before a new release is sent to the world, it's usually a good idea to do some housekeeping.


Python dependencies
:::::::::::::::::::

Python dependencies are managed by poetry.

To view "outdated" dependencies (dependencies with newer versions available), use:

.. code-block:: shell

    poetry show --latest --outdated

It is possible to explain why a dependency is installed using:

.. code-block:: shell

    # With development dependencies
    poetry show --tree


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
