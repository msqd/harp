Getting Started
===============

To get started with the rules engine, you need to write a configuration file that defines the rules you want to apply:

.. include:: examples/rules.inc

Loading
:::::::

.. versionadded:: 0.8

The ``rules`` application is loaded by default when using the ``harp-proxy server`` command.
It can be disabled by passing the ``--disable rules`` option to the command.

.. code:: shell

    harp-proxy server --disable rules ...
