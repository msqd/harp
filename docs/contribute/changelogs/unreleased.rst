Unreleased
==========


Added
:::::

* Stream attribute in both HttpRequest and HttpResponse to allow handling streaming objects and to get closer to httpx interfaces.
* Notifications Application, a simple way to send notifications to a slack or a google chat webhook to catch errors.

Changed
:::::::

* Removed WrappedHttpRequest, inner HttpRequests can now be accessed directly.

Fixed
:::::

* Ability to mock the Asgi bridge properly
