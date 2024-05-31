Command Line
============

.. click:: harp.commandline:entrypoint
   :prog: harp
   :nested: full

How to use
::::::::::

For PIP and source installs, it will be available as
`harp` in your python environment.

For source installations, you may need to use
`poetry run harp ...`.

Docker
------

For Docker installs, the harp CLI being the default command of the container you can pass arguments to the `docker run`
command directly.

.. code-block:: shell
    :emphasize-lines: 3

    docker run -it --rm \
           makersquad/harp-proxy \
           server --endpoint httpbin=4000:https://httpbin.org

Python package
--------------

For regular python installations (for example, using pip to install it from PyPI), you'll find the `harp` command in
your python environment's path, thus you'll be able to run:

.. code-block:: shell

    harp server --endpoint httpbin=4000:https://httpbin.org

Sources
-------

For sources installations, the behaviour is similar to installing it from a packaged wheel (python package), but you
may need to force using the right environment using poetry.

.. code-block:: shell

    poetry run harp server --endpoint httpbin=4000:https://httpbin.org

Another way would be to activate the poetry environment and run the command directly:

.. code-block:: shell

    poetry shell
    harp server --endpoint httpbin=4000:https://httpbin.org
