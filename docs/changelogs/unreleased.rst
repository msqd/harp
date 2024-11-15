Unreleased
==========

Added
:::::

* Proxy: it is now possible to add not exposed endpoints in the proxy configuration.
* Proxy: Custom controller types with custom settings can be added to the proxy configuration as services definitions.

Fixed
:::::

* DX: Add the ability to use --set x=y or --set x y (both equivalent) to all commands (@masterivanic, #590)
* UI: Correctly display header values containing a semicolon character (#577, @ArthurD1)
* UI: Fixed the topology UI where changing the state of a remote would cause the page to crash (#578, @ArthurD1).


Changed
:::::::

* Storage: The Engine is now defined as a service and instantiated using dependency injection. (#72, @ArthurD1)
