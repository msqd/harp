Unreleased
==========

Added
:::::

* Core/Http: Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get closer to httpx interfaces.

Changed
:::::::

* Config: the ``harp.config.BaseSetting``class has been renamed to ``harp.config.Settings``.
* Core/Http: Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.

