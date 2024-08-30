Dependency Injection
====================

HARP Proxy is a highly modular system that uses an :ref:`Inversion of Control (IoC) <ioc>` container to simplify
extending or modifying the system. This container implements automatic :ref:`Dependency Injection (DI) <di>`, based on
configuration files and type annotations. Along with the :doc:`Event Dispatcher <events>`, it provides all the tools you
need to write loosely coupled :doc:`Applications <applications>` (our term for extensions/plugins).

.. todo::

    - Add details the container configuration format
    - Add links to api reference for components described here
    - Add a section about the container conditionals
    - Add a section about the system-wide container intance (ref: dic)


.. _di:

Dependency Injection (DI)
:::::::::::::::::::::::::

Dependency injection is a software engineering technique where an object or function receives the objects or functions
it needs from an external source, rather than creating them internally. This technique separates the concerns of
constructing objects and using them, resulting in loosely coupled programs.

For example, consider a class that needs to interact with a database:

.. code-block:: python

    class Database:
        def __init__(self, host, port):
            self.host = host
            self.port = port

    class UserRepository:
        def __init__(self):
            self.database = Database('localhost', 5432)

        def find(self, **criteria):
            ...

    if __name__ == '__main__':
        user_repository = UserRepository()
        user_repository.find(name='Alice')
        user_repository.find(name='Bob')
        ...

This simple example, that does not use dependency injection, has a few issues:

1. The `UserRepository` class is tightly coupled to the `Database` class, making it difficult to test in isolation.
2. The `Database` class is created internally by the `UserRepository` class, making it difficult to swap out different
   database implementations.
3. The `Database` class is created with hardcoded values, making it difficult to configure it externally.

Instead, we can use dependency injection to make things more flexible:

.. code-block:: python

    class UserRepository:
        def __init__(self, database):
            self.database = database

        def find(self, **criteria):
            ...

    if __name__ == '__main__':
        database = Database('localhost', 5432)
        user_repository = UserRepository(database)
        user_repository.find(name='Alice')
        user_repository.find(name='Bob')
        ...

It is now easy to test each component in isolation, swap out different database implementations, and the instance
creation being externalized, it is now possible to configure the database without passing all settings to the
parent/owner class.

This is a quite simple concept, shown on a quite simple example. In real-world applications like
`HARP Proxy <https://harp-proxy.net>`_, dependency injection is widely used to make the code more modular, testable,
and maintainable, and you should think about it when writing your code.

Dependency Injection is a concept that does not require any tools or libraries to be implemented, it's just a good
practice that you can and should apply when writing code.


.. _ioc:

Inversion of Control (IoC)
::::::::::::::::::::::::::

Inversion of Control (IoC) is a design principle where the control of object creation and management is transferred from
the application code to a container or framework, which automatically provides dependency injection.

This approach allows for more flexible and modular code, as dependencies are injected into objects rather than being
created by them.

There are a lot of ways to implement IoC. A common way is to use a Dependency Injection Container, a component that
will be configured using service definitions (with their relations) and will be responsible for creating and managing
the instances of the services.

Here is a conceptual example (not actual working code) with our previous classes:

.. code-block:: python

    # build a coherent collection of service definitions
    container = Container()
    container.add_service('database', Database, host='localhost', port=5432)
    container.add_service('user_repository', UserRepository, database=Service('database'))

    # compile the container into a graph of services
    provider = container.build_provider()

    # ... then later in the code ...

    # get the user repository from the provider, which will create the database and the user repository if necessary
    user_repository = provider.get('user_repository')

Python's type annotations
-------------------------

This is the basic idea behind IoC, but we can do better. First, we can use python's annotation to make the definitions
less verbose:

.. code-block:: python

    class Database:
        def __init__(self, host: str, port: int):
            self.host = host
            self.port = port

    class UserRepository:
        def __init__(self, database: Database):
            self.database = database

    if __name__ == '__main__':
        # then, the container
        container = Container()
        container.add_service(Database)
        container.add_service(UserRepository)
        provider = container.build_provider()

        # and later in the code
        user_repository = provider.get(UserRepository)

The type annotations may be used to resolve the dependencies, making the code easier to understand and the dependency
definition sits in the place you will look for it: the class definition.

Configuration
-------------

To go further (and step by step, to the HARP implementation), we can move the service definitions to a configuration
file.

.. code-block:: yaml

    services:
      - name: database
        type: Database
        arguments:
          host: localhost
          port: 5432
      - name: user_repository
        type: UserRepository
        arguments:
          database: !ref 'database'

The container will then be able to read this file to build the services graph accordingly. Here, the arguments of the
``user_repository`` service are resolved using the ``!ref`` YAML constructor, which is a way to reference another
service explicitely. In this example, the ``database`` argument is not necessary (as it will be resolved using the type
annotation), but sometimes it's necessary to specify the dependencies explicitly.

.. code-block:: python

    if __name__ == '__main__':
        container = Container()
        container.load('services.yml')
        provider = container.build_provider()

        # get by name
        user_repository = provider.get("user_repository")

        # alternatively, get by type
        user_repository = provider.get(UserRepository)


Settings
--------

You can notice that configuration values are hardcoded, which is not what we want. Instead, we can use the ``!cfg``
yaml macro to retrieve values from the settings, with eventual default values:

.. code-block:: yaml

    services:
      - name: database
        type: Database
        arguments:
          host: [!cfg 'database.host', 'localhost']
          port: [!cfg 'database.port', 5432]
      - name: user_repository
        type: UserRepository
        arguments:
          database: !ref 'database'

This way, the configuration is more flexible and can be changed without modifying the code, in userland.

.. code-block:: python

    settings = {
        'database': {
            'host': 'example.com',
            'port': 1234
        }
    }

    if __name__ == '__main__':
        container = Container()
        container.load('services.yml', bind_settings=settings)
        provider = container.build_provider()

        # ...

The ``!ref`` and ``!cfg`` YAML constructors are building references under the hood, lightweight objects that will be
resolved later.

The ``!ref`` YAML contructor will be resolved at the last moment, when the service is requested, and the ``!cfg`` YAML
constructor will be resolved when the configuration is bound (during the ``load`` call).

Conditionals
------------

Finally, sometimes the service existence itself is conditional. Some services will only be defined if some setting is
of a given value.

.. code-block:: yaml

    services:
      - name: database
        type: Database

      - user_repository:
        type: UserRepository

      - condition: [!cfg "database.type == 'sql'"]
        services:
          - name: database
            override: merge
            type: SqlDatabase
            arguments:
              host: [!cfg 'database.host', 'localhost']
              port: [!cfg 'database.port', 5432]

Examples
::::::::

You can read the actual :doc:`builtin applications service definition files <dependency-injection-examples>` for real-world examples.


Usage
:::::

When :doc:`writing your own applications <applications>`, you can define services using either the python API or the
declarative YAML configuration format (the later is advised). It will allow to define your own services, extend the
existing services or override them.
