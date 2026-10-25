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

Today accounts sign in with the **Basic** authentication of the dashboard (:doc:`/apps/dashboard/settings`). A user
declared there is an account that is created on first use, with the ``admin`` role, as it could already do everything.
Its role is then the one of the account, which is read from the database on every request: demoting or disabling an
account applies at once.

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

.. note::

    A dashboard explicitly left open (``dashboard.auth.type: none``) has no account to ask a role of: everything is
    allowed, and favourites are the ones of the ``anonymous`` account, as before.


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

.. note::

    The command does not set a password yet: until password sign-in lands, an account signs in through a user of the
    same name declared in ``dashboard.auth``.


Upgrading
:::::::::

- **PostgreSQL**: the first revision of the ``auth`` branch renames ``users`` to ``auth_accounts`` and gives the
  existing rows the ``person`` kind and the ``admin`` role, ``anonymous`` becoming a ``viewer`` ``system`` account.
  ``harp-proxy db:migrate down auth@base`` gives ``users`` back, which fails if a username is longer than 32
  characters. See :doc:`/operate/migrations`.
- **SQLite** is never migrated by alembic: a file written by an earlier version is refused at start, delete it (it is
  recreated) or run ``harp-proxy db:reset``.
- **MySQL and MariaDB** are deprecated and not migrated: the revision logs a warning and does nothing.
- An ``applications:`` list in your configuration must now include ``auth`` for the dashboard to start.


Loading
:::::::

The ``auth`` application is loaded by default, before the dashboard. It can be disabled with ``auth.enabled: false``,
as long as the dashboard is (the dashboard requires it).
