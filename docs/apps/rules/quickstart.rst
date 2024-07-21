Getting Started
===============

To get started with the rules engine, you need to write a configuration file that defines the rules you want to apply:

.. include:: examples/rules.rst

Then make sure that you enable the ``rules`` application, and load the configuration file you just wrote:

.. tab-set::
    :sync-group: code

    .. tab-item:: TOML
        :sync: toml

        .. code:: shell

            harp start --enable rules -f my-rules.toml

    .. tab-item:: YAML
        :sync: yaml

        .. code:: shell

            harp start --enable rules -f my-rules.yml
