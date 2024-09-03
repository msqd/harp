HTTP Client Services
====================

.. tags:: services

The services defined by the ``http_client`` application are listed below, and will vary depending on settings.

When cache is enabled
:::::::::::::::::::::

When the cache is enabled, the following services are available:

.. autoservices:: harp_apps.http_client
   :file: ../../../harp_apps/http_client/services.yml
   :namespace: http_client
   :settings: {"cache": {"enabled": true}}


When cache is disabled
::::::::::::::::::::::

When the cache is disabled, the following services are available:

.. autoservices:: harp_apps.http_client
   :file: ../../../harp_apps/http_client/services.yml
   :namespace: http_client
   :settings: {"cache": {"enabled": false}}
