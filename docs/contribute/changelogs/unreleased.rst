Added
:::::

* Redis support for blob storage.

Changed
:::::::

* Blob storage is now separated from the main storage, to allow different underlying implementations.
* Application ``harp_apps.sqlalchemy_storage`` was renamed to ``harp_apps.storage``, to reflect the fact that
  ``sqlalchemy`` is an implementation detail, and that it now handles more than just sql or sqlalchemy-based storage.
