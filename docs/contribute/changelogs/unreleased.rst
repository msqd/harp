Unreleased
==========


Added
:::::

* Core/Http: Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get
  closer to httpx interfaces.
* Proxy: Added support for multiple remote urls for a given endpoint.
* Proxy: Added support for default/fallback pools in remote configuration for resilience.
* Proxy: Added a simple but functional circuit breaker implementation.
* Proxy: Add probe implementation in background.
* Core: Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get closer to httpx interfaces.
* Notifications: Implements a simple way to send notifications to a slack or a google chat webhook to catch errors.

Changed
:::::::

* Config: the settings are now implemented using pydantic, with more strictness so that settings only contains settings
  and state-related things are moved to wrappers. The new ``harp.config.Configurable`` base class is now used for all
  settings classes, and a new ``harp.config.Stateful`` allows to define settings wrappers for stateful objects.
* Core/Http: Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.
* DX: adds a ``harp examples list`` command to list available examples
* DX/Core: HttpRequest can now be instanciated without an explicit implementation. If no implementation is provided,
  then the kwargs data is passed to a stub implementation, allowing a simpler way to create requests (in tests, for
  example).
* DX/Helm: adds the ability to override environment in helm chart's values



Fixed
:::::

* Storage: added missing index on messages.transaction_id to speed up dashboard search queries.
