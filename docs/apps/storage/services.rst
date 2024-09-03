Storage Services
================

.. tags:: services

The services defined by the ``storage`` application are listed below, and will vary depending on settings.

With SQL blob storage
:::::::::::::::::::::

When the blob storage is of "sql" type, the following services are available:

.. autoservices:: harp_apps.storage
   :namespace: storage
   :file: ../../../harp_apps/storage/services.yml
   :settings: {"blobs": {"type": "sql"}}


With Redis blob storage
:::::::::::::::::::::::

When the blob storage is of "redis" type, the following services are available:

.. autoservices:: harp_apps.storage
   :namespace: storage
   :file: ../../../harp_apps/storage/services.yml
   :settings: {"blobs": {"type": "redis"}}

To customize the Redis client, you can override the ``blobs.redis`` settings in your configuration:

.. literalinclude:: ./examples/redis.yml
    :language: yaml
