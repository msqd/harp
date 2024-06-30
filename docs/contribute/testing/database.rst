Database-related tests
======================

.. note::

    This page mostly consists of internal notes, for now. That can be useful for you too, but it may be very succint and
    lacking a lot of context / infos.

Database-related tests will spawn docker containers during the tests (using testcontainers) to test things.

Tests that use Storage
:::::::::::::::::::::::

Tests using storage can be writen either by subclassing :class:`StorageTestFixtureMixin
<harp_apps.storage.utils.testing.mixins.StorageTestFixtureMixin>` and then using the `storage`
fixture or by using the lower-level tools.

Using `StorageTestFixtureMixin` and the  ``storage`` fixture
----------------------------------------------------------------------

.. code-block::

    from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

    class TestMyFeature(StorageTestFixtureMixin):
        def test_my_feature(self, storage):
            ...


Using the ``database_url`` fixture
----------------------------------

.. code-block:: python

    from harp.utils.testing.databases import parametrize_with_database_urls

    @parametrize_with_database_urls()
    def test_my_feature(database_url):
        ...

.. warning:: This won't create an isolated database.


Limiting to a subset of supported databases
-------------------------------------------

Some tests have no reason to run on all supported databases, espacially if they are testing an implementation specific
feature. Some examples of this are tests around the ``pg_tgrm`` extension usage and the associated indexes, as this is
a postgresql feature, or migrations which are not used for sqlite.

Use the :func:`@parametrize_with_database_urls(...) <harp.utils.testing.databases.parametrize_with_database_urls>`
decorator to change the behaviour of ``database_url`` (and ``storage``, which depends on it) fixture.

.. code-block::

    class TestMyPostgresqlSpecificFeature(StorageTestFixtureMixin):
        @parametrize_with_database_urls('postgresql')
        def test_my_postgresql_specific_feature(self, database_url):
            ...

        @parametrize_with_database_urls('postgresql')
        def test_my_postgresql_specific_feature(self, storage):
            ...

    class TestSomeWiderSpecificFeature(StorageTestFixtureMixin):
        @parametrize_with_database_urls('postgresql', 'mysql')
        def test_my_not_really_specific_feature(self, storage):
            ...


Using the lower-level tools
---------------------------

You can use your regular python debugger to interrupt a test, and connect to the underlying database container while
your test is interrupted.

.. code-block:: shell

    docker ps
    docker exec -it <container_id> psql -U test

You'll have superadmin privilege, you now need to find the right database and use it:

.. code-block:: shell

    test=# \l              # list databases
    test=# \c test_af42ea  # connect to the chosen database
    test_af42ea=# \dt      # list tables

Each db test will have it's own database, hence the unique hash.

More helpers
------------

.. todo:: to do be do be do (Frank Sinatra)


Instrumenting the storage
-------------------------

The storage can be instrumented to log all the queries it receives. This can be useful to debug tests, or even to write
tests that needs to access to the sql queries (can count, chek content, explain analyze, ...).

Once you get a storage, call
:func:`install_debugging_instrumentation() <harp_apps.storage.storage.Storage.install_debugging_instrumentation>`
on your instance and all sql queries will find their way into ``your_storage.sql_queries``.

.. code-block:: python

    from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

    class TestWithInstrumentation(StorageTestFixtureMixin):
        @parametrize_with_database_urls("postgresql")
        async def test_sql_queries_instrumentation(self, storage):
            # create a rich console to display the queries with syntax highlighting
            console = Console(force_terminal=True, width=120)

            # instrument the storage to store queries
            storage.install_debugging_instrumentation()

            try:
                result = await storage.get_transaction_list(username="anonymous", with_messages=True, text_search="bar")
                assert len(storage.sql_queries) == 2

                for query in storage.sql_queries:
                    print("*** SQL QUERY ***")
                    console.print(Syntax(query, "sql", word_wrap=True, theme="vs"))
                    explained = await run_postgres_explain_analyze(storage.engine, query)
                    print("*** EXPLAIN ANALYZE ***")
                    print(explained)

            finally:
                await opt.engine.dispose()


An optional ``echo=True`` keyword argument can be passed to the ``install_debugging_instrumentation`` method to enable
full sql logs, including for postgresql an additional log of "explain analyze" for each query (query plan).

.. todo:: move to a project test file so that the example run in test suite.
