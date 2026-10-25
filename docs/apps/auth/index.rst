Auth
====

.. tags:: applications

.. versionadded:: 0.13

The ``harp_apps.auth`` application owns who may use HARP: the **accounts**, the **role** each one holds, and the
**actor** a request stands for. The dashboard depends on it, so it is loaded whenever a dashboard is.

.. toctree::
    :hidden:
    :maxdepth: 1

    Settings <settings>
    Internals </reference/apps/harp_apps.auth>


Accounts
::::::::

An account is something that signs in to HARP and holds a role: a person, or a machine. Accounts live in the
``auth_accounts`` table of the :doc:`storage </apps/storage/index>` database, which replaces the former ``users``
table. Favourites keep their author.

``username``
    Unique, up to 255 characters.

``display_name``
    Optional, shown in the dashboard header in place of the username.

``email``
    Optional and unique whatever the case: it is stored lower-cased. It is shown, and never a way in.

``kind``
    ``person``, ``machine`` or ``system``. ``anonymous``, the author of the favourites recorded before there were
    accounts, is a ``system`` account: no request is ever attributed to it, and a ``system`` account cannot sign in.

``role``
    ``viewer``, ``editor`` or ``admin``, see below.

``created_at``, ``last_seen_at``, ``disabled_at``
    ``last_seen_at`` is written at most once a minute. A disabled account answers ``401`` at its next request.

Today accounts sign in with the **Basic** authentication of the dashboard (:doc:`/apps/dashboard/settings`). The users
declared there are **imported once** per database, at the first start with the ``auth`` application: each becomes an
enabled ``admin`` person (an account that already exists is enabled and made ``admin``), and a ``system`` account
named ``basic-import`` records that it ran. Later starts import nothing: a configured user without an account, because
it was deleted or added to the configuration afterwards, answers ``401``. The role is the one of the account, read from
the database on every request: demoting or disabling an account applies at once.

Roles
:::::

Roles are ordered, each one includes what the one below it may do.

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - Role
      - May use
    * - ``viewer``
      - The overview, the transactions and their bodies, the metrics, and its own favourites.
    * - ``editor``
      - Also the topology, the storage state, and taking a remote endpoint up or down
        (``PUT /api/system/proxy``).
    * - ``admin``
      - Also the settings and the dependencies.

Every dashboard route declares the role it requires, and a request below it is answered ``403``. A route added
without a declared role is reserved to ``admin``. The dashboard shows the account and its role in its header, and
does not offer the pages the role cannot use.

.. warning::

    A dashboard explicitly left open (``dashboard.auth.type: none``) has no account to ask a role of: everything is
    allowed, and favourites are the ones of the ``anonymous`` account, as before. This is a **temporary deviation** from
    the design, which has no open mode; it is removed when password sign-in lands (#1520).


The actor
:::::::::

Resolving a request yields one **actor**: the account, the role the request acts with (the *effective* role), how it
got in (``via``, with ``via_id`` naming the credential) and the client acting on its behalf, if any. Controllers and
role checks read this and nothing else (:mod:`harp.security.actor`).

The effective role is the lowest of the role of the account and the cap of the credential. Basic has no cap, so for now
it is the role of the account.


Commands
::::::::

.. code-block:: shell

    harp-proxy auth:create-account alice --role editor --display-name "Alice" --email alice@example.com

creates an account. It is also the way back in when no Admin is left: create one, the role is read at each request so
there is nothing to restart. The command refuses a username or an email that is taken, and a database whose schema is not
current.

.. code-block:: shell

    harp-proxy auth:set-role alice admin
    harp-proxy auth:disable-account alice
    harp-proxy auth:enable-account alice

change the role of an account, and revoke or restore it. **Revoke by disabling**: a disabled account answers ``401`` at
its next request and nothing is lost. Never delete a row: the favourites of the account go with it. These commands are
the way to manage accounts until the administration screen exists.

.. note::

    The command does not set a password yet: until password sign-in lands, an account signs in through a user of the
    same name declared in ``dashboard.auth``.


Upgrading
:::::::::

- **PostgreSQL**: the first revision of the ``auth`` branch renames ``users`` to ``auth_accounts``. The rows that
  existed become **disabled** ``viewer`` people, so nobody gets access from the migration; ``anonymous`` becomes an
  enabled ``viewer`` ``system`` account. The one-time import of the Basic users then enables the configured ones, as
  ``admin``. Enable any other with ``auth:enable-account`` and ``auth:set-role``.
  ``harp-proxy db:migrate down auth@base`` gives ``users`` back, which fails if a username is longer than 32
  characters. See :doc:`/operate/migrations`.
- **SQLite** is never migrated by alembic: a file written by an earlier version is refused at start, delete it (it is
  recreated) or run ``harp-proxy db:reset``.
- **MySQL and MariaDB** are deprecated and not migrated: the revision logs a warning and does nothing.


Loading
:::::::

The dashboard declares ``auth`` in its dependencies, so ``auth`` is loaded whenever the dashboard is, before it, even
when an ``applications:`` list does not name it (:doc:`/develop/run`). A HARP without dashboard loads no ``auth``.
