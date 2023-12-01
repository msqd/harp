Storage
=======

Harp can store data about transactions for later inspection and supports different storage engines. We call this
transaction audit. Decision about whether or not to store data is made first globally then on a request basis.

Harp 1.x only supports one storage engine at a time, as it is quite edge case to need more than one for a given
instance.

Storage engine is configured under the ``storage`` namespace, with the ``engine`` key selecting which implementation to
use. Engine specific settings are documented under each section below.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          engine: <name>
          ...

    .. code-block:: json

        {
          "storage": {
            "engine": "<name>",
            ...
          }
        }

    .. code-block:: toml

        [storage]
        engine = "<name>"
        ...

    .. code-block:: ini

        [storage]
        engine = <name>
        ...

    .. code-block:: env

        export HARP_STORAGE_ENGINE=<name>
        ...

    .. code-block:: python

        from harp import ProxyFactoy

        settings = {
            'storage': {
                'engine': '<name>',
                ...
            }
        }

        proxy = ProxyFactory(settings=settings)

        if __name__ == "__main__":
            proxy.run()

.. attribute:: storage.engine

    Name of the storage engine to use. Defaults to ``memory``.

    Engines are described below with the specific settings they support.


Engines
:::::::


In Memory
---------

The default storage engine is a naive "in memory" implementation that stores data in a deque (double ended queue),
limited to a fixed amount of elements. Although it is not suited for production usage, it does not require any external
service and allows to start a service without any additional setup.

If you're using in memory storage, a warning will show at startup to remind you the caveats of this engine.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          engine: memory
          max_size: 1000

    .. code-block:: python

        from harp import ProxyFactoy

        settings = {
            'storage': {
                'engine': 'memory',
                'memory': {
                    'max_size': 1000
                }
            }
        }

        proxy = ProxyFactory(settings=settings)

        if __name__ == "__main__":
            proxy.run()

    .. code-block:: env

        export HARP_STORAGE_ENGINE=memory
        export HARP_STORAGE_MEMORY_MAX_SIZE=1000

    .. code-block:: json

        {
          "storage": {
            "engine": "memory",
            "max_size": 1000
          }
        }

    .. code-block:: toml

        [storage]
        engine = "memory"
        max_size = 1000

    .. code-block:: ini

        [storage]
        engine = memory
        max_size = 1000

.. attribute:: storage.max_size

    Maximum number of elements to store in memory. Defaults to ``1000``.

SQL Database
------------

.. tab-set-code::

    .. code-block:: yaml

        storage:
          engine: database
          dialect: postgresql

.. attribute:: storage.dialect

    `SQLAlchemy dialect <https://docs.sqlalchemy.org/en/20/dialects/>`_ to use. Defaults to ``postgresql``.

    Please note that as of now, only ``postgresql`` is supported (although other dialects may work).


SQL Database (async)
--------------------
