Introduction
============

We'll guide you through the process of seting up a development environment, opening and understanding the architecture
and concepts used, navigationg through the codebase, and finally writing code, including tests.


Getting started
:::::::::::::::

To get started, you need the following tools installed on your machine:

- A working Python 3.12 environment with the ``poetry`` package manager installed.
- A working NodeJS (lts/iron) environment with the ``pnpm`` package manager installed.
- A working Docker + Docker Compose environment.
- Git and GNU Make

Clone the repository:

.. code-block:: bash

    git clone git@github.com:msqd/harp.git

Install the dependencies:

.. code-block:: bash

    cd harp
    make install-dev

This will install the dependencies and set up the development environment.

To check that everything is working, we strongly recommend running the full test suite:

.. code-block:: bash

    make qa

Congratulations, you're ready to start writing HARP code!
