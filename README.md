https://asgi.readthedocs.io/en/latest/introduction.html

Run example with reload
=======================

watchfiles --filter python 'python examples/basic.py' harp examples

Design choices
==============

* We use hypercorn because it's way easier to map multiple ports than uvicorn. Even uvicorn author finds the api better.
  see https://pgjones.gitlab.io/hypercorn/how_to_guides/configuring.html ?

Misc ideas
==========

* Filter with jq ? Sounds mega slow. But in some cases, may be usefull.

https://pypi.org/project/jq/

* regex matching

https://github.com/intel/hyperscan

TSDB
====

https://docs.tdengine.com/develop/query-data/
https://tdengine.com/devops-performance-comparison-influxdb-and-timescaledb-vs-tdengine/
https://github.com/timescale/timescaledb

timescale prob better option to have pg behind for stability, power and other stuff not ts related


Marketing
=========

for developpers

less code, more robust, avoid repetitive hard code (cache, retry, timeouts ...), debugging

for operations

secure by default, adds observability

for executives

reduce development and maintenance cost of API related code
audited by default, adds security

rgpd : need a way to anonymize payloads
