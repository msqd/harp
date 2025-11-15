HTTP Client Settings
====================

.. tags:: settings

Examples
::::::::

Here is an example containing all default values for the ``http_client`` application settings.

.. literalinclude:: ./examples/reference.yml
    :language: yaml

Reference
:::::::::

Implementation (python): :class:`HttpClientSettings <harp_apps.http_client.settings.HttpClientSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/HttpClientSettings

.. note::

   For cache settings, see the :doc:`http_cache settings </apps/http_cache/settings>` documentation.
