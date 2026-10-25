Dashboard
=========

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.dashboard`` application implements the administrative api and micro-frontend.

If enabled, a server will be available (by default, on port `4080`) to access the :doc:`HARP Dashboard
</features/dashboard>` and observe whatever goes through the proxy.

It listens on ``dashboard.host``, which defaults to ``[::]`` (every interface) so a published Docker port keeps working.
Set ``host: 127.0.0.1`` to serve it on the loopback interface only. The startup warning about the dashboard login or
about disabled authentication names the address it listens on. ``dashboard.host`` applies to the dashboard port only,
not to ``metrics_port``, which keeps listening on ``[::]``.

.. toctree::
    :hidden:
    :maxdepth: 1

    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.dashboard>


Loading
:::::::

The dashboard application is loaded by default. You can :code:`--disable` it if you want.

.. code-block:: shell

    $ harp-proxy server ... --disable dashboard

.. todo::

    Implement CLI to load or not load an application.


Configuration
:::::::::::::

.. note::

    The dashboard is enabled by default and configured with reasonable defaults.

Main
----

Main settings for the dashboard.

.. literalinclude:: ./examples/main.yml
    :language: yaml

Internal implementation: :class:`DashboardSettings <harp_apps.dashboard.settings.DashboardSettings>`

Authentication
--------------

Configuration for dashboard user authentication.

**By default, the dashboard requires a login.** Without ``dashboard.auth``, HARP generates a random password for the
``admin`` user at each start and logs it once:

.. code-block:: text

    Dashboard login (generated for this boot only): username=admin password=<password> ...

The password is new at every start, kept only as a hash in memory, and never shown in the settings, the storage or any
other log line. Every route of the dashboard port is behind it, ``/metrics`` included. In a container, read it with
``docker logs <container>``.

To choose your own users, configure basic authentication: nothing is generated then.

.. literalinclude:: ./examples/auth.yml
    :language: yaml


.. literalinclude:: ./examples/auth.basic.yml
    :language: yaml

Internal implementation: :class:`BasicAuthSettings <harp_apps.dashboard.settings.auth.BasicAuthSettings>`

.. include:: ./_howto_auth_hash.rst

Each user is an account of the :doc:`auth application </apps/auth/index>`, which gives it a role (``viewer``,
``editor`` or ``admin``) that decides the pages and actions it may use. Users declared here are ``admin``.

To explicitly serve the dashboard without authentication, set the type to ``none`` (or
``--set dashboard.auth.type=none``).

.. literalinclude:: ./examples/auth.none.yml
    :language: yaml

.. warning::

    An unauthenticated dashboard exposes everything that goes through the proxy to anyone who can reach its port. HARP
    logs a warning at every start. Only use it behind a network boundary you trust.

Metrics port
------------

``dashboard.metrics_port`` opens a second port serving only ``/metrics``, **unauthenticated by design**, so Prometheus
can scrape it without credentials. Any other path there answers 404. Keep it on a private network. See
:doc:`/operate/prometheus`.


Security headers
----------------

Every dashboard response carries ``X-Content-Type-Options: nosniff`` and ``X-Frame-Options: DENY`` and ``Referrer-Policy: same-origin``; the built
dashboard also sends a ``Content-Security-Policy`` that allows only its own scripts, styles and API, and forbids
framing (``frame-ancestors 'none'``). The dashboard cannot be embedded in another page.

Requests that change state (``PUT``, ``POST``, ``DELETE``) are refused unless they are ``application/json`` and come
from the dashboard itself: a cross-site ``Origin`` or ``Sec-Fetch-Site`` is answered ``403``, a missing JSON content
type ``415``. Scripts calling these routes must send ``Content-Type: application/json``.

Captured message bodies (``/api/blobs/{id}``) are served with ``Content-Disposition: attachment`` and
``Content-Security-Policy: sandbox; default-src 'none'``: opening one in a browser downloads it, and it never runs as
a page of the dashboard.


Dev Server
----------

Explicit configurations for the dashboard's micro frontend dev server, served by vitejs.

.. literalinclude:: ./examples/devserver.yml
    :language: yaml

.. admonition:: Internal

    You most likely don't need to configure the dev server unless you're working on harp's internals.

Enable/disable
--------------

To disable the dashboard globally, do not load the ``dashboard`` application.

.. code-block:: shell

    $ harp-proxy server ... --disable dashboard
