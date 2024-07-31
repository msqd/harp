Unreleased
==========


Added
:::::

* Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get closer to httpx interfaces.

Changed
:::::::

* Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.

Fixed
:::::

* Ability to mock the Asgi bridge properly
