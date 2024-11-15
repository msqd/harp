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

* Proxy: Endpoints can now include full paths beyond just base paths. For example, URLs like http://example.com/api/v1/endpoint1/ are now supported in addition to simpler base URLs like http://example.com/. (#35, @ArthurD1)
