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

Changed
:::::::

* Config: the ``harp.config.BaseSetting``class has been renamed to ``harp.config.Settings``.
* Core/Http: Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.
* DX: adds a ``harp examples list`` command to list available examples
