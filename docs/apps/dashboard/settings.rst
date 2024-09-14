Dashboard Settings
==================

.. tags:: settings

Examples
::::::::

Here is an example containing all default values for the ``dashboard`` application settings.

.. literalinclude:: ./examples/reference.yml
    :language: yaml

Reference
:::::::::

Implementation (python): :class:`DashboardSettings <harp_apps.dashboard.settings.DashboardSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/DashboardSettings

.auth
-----

Implementation (python): :class:`BasicAuthSettings <harp_apps.dashboard.settings.auth.BasicAuthSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/BasicAuthSettings


.devserver
----------

Implementation (python): :class:`DevServerSettings <harp_apps.dashboard.settings.devserver.DevserverSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/DevserverSettings
