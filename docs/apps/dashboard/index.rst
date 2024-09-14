Dashboard
=========

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.dashboard`` application implements the administrative api and micro-frontend.

If enabled, a server will be available (by default, on port `4080`) to access the :doc:`HARP Dashboard
</features/dashboard>` and observe whatever goes through the proxy.

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

    $ harp start ... --disable dashboard

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

.. literalinclude:: ./examples/auth.yml
    :language: yaml


.. literalinclude:: ./examples/auth.basic.yml
    :language: yaml

Internal implementation: :class:`DashboardAuthSetting <harp_apps.dashboard.settings.DashboardAuthSetting>`,
:class:`DashboardAuthBasicSetting <harp_apps.dashboard.settings.DashboardAuthBasicSetting>`

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

    $ harp start ... --disable dashboard
