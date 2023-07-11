
https://asgi.readthedocs.io/en/latest/introduction.html

Run example with reload
=======================

watchfiles --filter python 'python examples/basic/router.py' harp examples/basic

Misc
====

* Maybe use hypercorn ? Looks more flexible and supports multiple binds. Still need to route behind.

see https://pgjones.gitlab.io/hypercorn/how_to_guides/configuring.html ?

* Filter with jq ?

https://pypi.org/project/jq/