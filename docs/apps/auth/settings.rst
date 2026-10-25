Auth Settings
=============

.. tags:: settings

Examples
::::::::

Here is an example containing all default values for the ``auth`` application settings.

.. code-block:: yaml

    auth:
      enabled: true

Reference
:::::::::

Implementation (python): :class:`AuthSettings <harp_apps.auth.settings.AuthSettings>`

``enabled``
    Set to ``false`` to disable the application, which the dashboard requires. Default ``true``.
