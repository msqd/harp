Unreleased
==========


Added
:::::

* Core: Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get closer to
  httpx interfaces.
* Core/Http: Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get
  closer to httpx interfaces.
* Core/Services: Services definitions are now using a declarative configuration format, that can be loaded by
  applications. A sphinx extension was added to automatically document service definitions from applications.
* Notifications: Implements a simple way to send notifications to a slack or a google chat webhook to catch errors.
* Proxy: Added support for multiple remote urls for a given endpoint.
* Proxy: Added support for default/fallback pools in remote configuration for resilience.
* Proxy: Added a simple but functional circuit breaker implementation.
* Proxy: Add probe implementation in background.
* Frontend: Generate typescript types from models, using the intermediary json schema generation provided by pydantic.

Changed
:::::::

* Config: the settings are now implemented using pydantic, with more strictness so that settings only contains settings
  and state-related things are moved to wrappers. The new ``harp.config.Configurable`` base class is now used for all
  settings classes, and a new ``harp.config.Stateful`` allows to define settings wrappers for stateful objects.
* Config: Redis configuration is now separated from blob storage, as it may be used by much more than just blobs.
* Core: ``EVENT_CONTROLLER_VIEW`` event has been renamed to ``EVENT_CORE_VIEW`` for consistency with other event names.
* Core/Http: Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.
* Core/Http: HttpRequest can now be instanciated without an explicit implementation. If no implementation is provided,
  then the kwargs data is passed to a stub implementation, allowing a simpler way to create requests (in tests, for
  example).
* DX: adds a ``harp examples list`` command to list available examples
* DX/Helm: adds the ability to override environment in helm chart's values


Fixed
:::::

* Storage: added missing index on messages.transaction_id to speed up dashboard search queries.


Deleted
:::::::

* Config: old settings classes have been removed (Definition, DisableableBaseSettings, DisabledSettings, Lazy, Settings)
  along with related helper (settings_dataclass).
