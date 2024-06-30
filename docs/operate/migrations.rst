Database Migrations
===================

Database migrations are managed by `alembic`, a database migration  library for sqlalchemy. For now, we only have models
in the `storage` application, and the implementation shared between this application and the command line
package in the main `harp` package.

We use custom wrappers around the alembic CLI because we need to handle migrations slightly differently for different
database engines.


Running Migrations
::::::::::::::::::

To run migrations, you can either start your harp server with the `storage` application enabled and the
``storage.migrate = true`` setting (which are the default), or use the dedicated command line tool:

.. code-block:: shell

    # migrate to the latest revision, or «head»
    harp db:migrate up head

    # migrate down to a specific revision
    harp db:migrate down <revision>

    # migrate up to a specific revision
    harp db:migrate up <revision>

    # migrate down to the initial empty state
    harp db:migrate down base

Note that to run migrations, you'll need a valid storage configured.

To list available database versions, you can run:

.. code-block:: shell

    harp db:history

.. note:: Migrations have no effect for sqlite setups.

Configuration
:::::::::::::

By default, the storage application will migrate to the latest database revision on startup. This is convenient for
most cases, as you'll want the latest version of the database schema to be available with the latest harp version
installed, but it may not be desirable in some cases.

You can disable the automatic migrations by using the ``storage.migrate = false`` setting. This can be activated on
command line by adding ``--set storage.migrate=false`` to the command line arguments, using
a configuration file, or a mix of both (for example to have a good default and override it manually when you need it.

.. code-block:: yaml

    storage.migrate: false


Dialect-specific migrations and features
::::::::::::::::::::::::::::::::::::::::

Some database implementations allows us to implement specific optimizations.


MySQL (and MariaDB)
-------------------

MySQL and MariaDB will add full-text indexes to the searchable columns. This is done without any additional
configuration.


PostgreSQL (and TimescaleDB)
----------------------------

PostgreSQL can use the pg_trgm extension to implement full-text search. This extension is not enabled by default, but
you can install it with the associated GIN indexes using:

.. code-block:: shell

    harp db:feature add pg_trgm ...settings...


Writing migrations
::::::::::::::::::

To write migrations, the easiest way is to update models then run the autogeneration command:

.. code-block:: shell

    harp db:create-migration 'some short description'

You'll be able to edit the newly added migration file and then, you can migrate your database to apply changes. It is
recommended to squash migrations before submitting a merge request.

.. note:: This is only available in development environments.
