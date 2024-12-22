Quick Start
===========

Install & Bootstrap
:::::::::::::::::::

To start developing with HARP (create your own proxies with custom code), you need a few
things:

**Install HARP to be used as a CLI/dev tool**

.. code:: shell

    pipx install 'harp-proxy[dev]'

.. note::

    This will install an isolated instance of HARP that we'll mostly use to create new
    projects. It is possible to do it without, but this is the easiest.

**Bootstrap a new project**

.. code:: shell

    harp create project

Answer a few questions, and you're ready to go!


**Start your project**

.. code:: shell

    cd <your-project>
    make

This will install the dependencies (in a poetry-managed virtualenv) and start your proxy.

Next Steps
::::::::::

Congratulations, you created your first HARP project! Now you can start tuning it.

.. todo:: pointers
