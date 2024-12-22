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


.cache
------

Implementation (python): :class:`CacheSettings <harp_apps.http_client.settings.cache.CacheSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/CacheSettings
