Storage Settings
================

.. tags:: settings

Examples
::::::::

Here is an example containing all default values for the ``storage`` application settings.

.. literalinclude:: ./examples/reference.yml
    :language: yaml

Reference
:::::::::

Implementation (python): :class:`StorageSettings <harp_apps.storage.settings.StorageSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/StorageSettings


.blobs
------

Implementation (python): :class:`BlobStorageSettings <harp_apps.storage.settings.blobs.BlobStorageSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/BlobStorageSettings
