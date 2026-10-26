Auth Settings
=============

.. tags:: settings

Examples
::::::::

Here is an example containing all default values for the ``auth`` application settings.

.. code-block:: yaml

    auth:
      enabled: true
      session_idle_hours: 12
      session_max_hours: 168
      setup_link_hours: 72

Reference
:::::::::

Implementation (python): :class:`AuthSettings <harp_apps.auth.settings.AuthSettings>`

``enabled``
    Set to ``false`` to disable the application, which the dashboard requires: disable both. Default ``true``.

``session_idle_hours``
    Hours without a request after which a dashboard session ends. Enforced by the server. Default ``12``.

``session_max_hours``
    Hours after which a dashboard session ends whatever its activity. Enforced by the server. Default ``168`` (7 days).

``setup_link_hours``
    Hours a setup link stays valid. A new one is made at each start while no Admin exists. Default ``72``.
