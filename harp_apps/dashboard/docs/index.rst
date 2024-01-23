Dashboard
=========

The `harp.apps.dashboard` application implements the administrative api and micro-frontend.

If enabled, a server will be available (by default, on port `4080`) to observe whatever goes through the proxy.

Loading
:::::::

The dashboard application is loaded by default. If you need to explicitely load or unlaod it, use the `--load` and
`--unload` flags.

.. code-block:: shell

    $ harp start ... --load harp.apps.dashboard
    $ harp start ... --unload harp.apps.dashboard

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

Internal implementation: :class:`DashboardSettings <harp.apps.dashboard.settings.DashboardSettings>`

Authentication
--------------

Configuration for dashboard user authentication.

.. literalinclude:: ./examples/auth.yml
    :language: yaml


.. literalinclude:: ./examples/auth.basic.yml
    :language: yaml

Internal implementation: :class:`DashboardAuthSetting <harp.apps.dashboard.settings.DashboardAuthSetting>`,
:class:`DashboardAuthBasicSetting <harp.apps.dashboard.settings.DashboardAuthBasicSetting>`

Dev Server
----------

Explicit configurations for the dashboard's micro frontend dev server, served by vitejs.

.. literalinclude:: ./examples/devserver.yml
    :language: yaml

.. admonition:: Internal

    You most likely don't need to configure the dev server unless you're working on harp's internals.




Enable/disable
--------------

To disable the dashboard globally, set `dashboard.enabled` to `false`.

.. tab-set-code::

    .. code-block:: yaml

        dashboard:
            enabled: false

    .. code-block:: shell

        $ harp start ... --set dashboard.enabled=false


.. todo::

    Implement CLI to load or not load an application.

    You can also disable the dashboard by not loading the `harp.apps.dashboard` application.

    .. code-block:: shell

        $ harp start ... --disable harp.apps.dashboard
