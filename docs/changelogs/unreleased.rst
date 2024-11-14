Unreleased
==========

Added
:::::

* Proxy: it is now possible to add not exposed endpoints in the proxy configuration.
* Proxy: Custom controller types with custom settings can be added to the proxy configuration as services definitions.

Changed
:::::::

* API: the `EVENT_READY` and `EVENT_SHUTDOWN` core events now takes (and provides) an `ASGIApplication` insteas of an
  `ASGIKernel` to avoid having a misleading interface when multiple ASGI middlewares are applied. The same change has
  been propagated to ``System``/``SystemBuilder``.

Fixed
:::::

* DX: Add the ability to use --set x=y or --set x y (both equivalent) to all commands (@masterivanic, #590)
* UI: Correctly display header values containing a semicolon character (#577, @ArthurD1)
* UI: Fixed the topology UI where changing the state of a remote would cause the page to crash (#578, @ArthurD1).
