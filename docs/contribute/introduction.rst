Introduction
============

We'll guide you through the process of :doc:`setting up a development environment <introduction>`, opening and
understanding the :doc:`architecture <architecture>` and concepts used (like :doc:`dependency injection
<dependency-injection>` and :doc:`event-driven hooks <events>`), navigating through the codebase, and finally writing
code, including tests.

System requirements
:::::::::::::::::::

You will need the following tools installed on your machine:

- Git and GNU Make
- A working Python 3.12 environment with the ``poetry`` package manager installed. We usually tend to use the latest
  stable version of Python.
- A working NodeJS (lts/iron) environment with the ``pnpm`` package manager installed.
- A working Docker + Docker Compose environment.

.. note::

    * :doc:`./misc/ubuntu`

Source code
:::::::::::

Once the system requirements are met, you can download the source code, using ``git clone``:

.. code-block:: bash

    git clone git@github.com:msqd/harp.git

Install the project's dependencies (isolated):

.. code-block:: bash

    cd harp
    make install-dev

This will install the dependencies in a separate virtual environment (managed by poetry) and set up the development
environment.

.. note::

    Depending on your system, you may get a warning about playwright not finding the system dependencies it needs. This
    is only required if you want to run the browser based tests, and can be safely ignored. On a linux system, you can
    install the missing dependencies with:

    .. code-block:: bash

        (cd harp_apps/dashboard/frontend; pnpm exec playwright install-deps)

Running
:::::::

You can start your first HARP server based on your local working copy, we'll use one of the built-in examples:

.. code-block:: bash

    poetry run harp start --example sqlite

Open your browser at http://localhost:4080 to have a look at the HARP dashboard.


Interfaces
::::::::::

The main developer interface is a ``Makefile``, containing the most common tasks you'll need to run. Get a list by
running:

.. code-block:: bash

    make help

For anything requiring a valid environment to run, you can use the ``poetry run harp`` command, which will run the HARP
CLI within the poetry-managed virtualenvironment.


Next steps
::::::::::

Congratulations, you're ready to start writing HARP code! Before that, you may want to have a glance at the following
topics:

- :doc:`./overview`
- :doc:`./applications`
