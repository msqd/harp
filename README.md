
https://asgi.readthedocs.io/en/latest/introduction.html

Run example with reload
=======================

watchfiles --filter python 'python examples/basic.py' harp examples

Misc
====

* Maybe use hypercorn ? Looks more flexible and supports multiple binds. Still need to route behind.

see https://pgjones.gitlab.io/hypercorn/how_to_guides/configuring.html ?

* Filter with jq ?

https://pypi.org/project/jq/


TSDB
====

https://docs.tdengine.com/develop/query-data/
https://tdengine.com/devops-performance-comparison-influxdb-and-timescaledb-vs-tdengine/
https://github.com/timescale/timescaledb

timescale prob better option to have pg behind for stability, power and other stuff not ts related
