Execution
=========

Trust model
:::::::::::

Rules are code written by whoever administers the proxy, and they run inside the proxy process with its privileges.
Isolation here is about one rule not breaking another, not about containing hostile code: never load a rule from a
source you do not trust.

Each script runs with fresh globals: a copy of the builtins plus the context of its lifecycle event (see the context
reference of each event). A ``global`` statement, a variable or a function defined by one script is invisible to the
others, and a function defined in a script sees the context (``request``, ``response`` ...). What a script assigns to
a name of the context, ``response = ...`` for example, is taken into account after it ran. The objects of the context
(request, response, transaction) are the live ones, shared with the proxy.

Failure policy
::::::::::::::

When a script raises an exception, or fails otherwise (an invalid response, a time budget exceeded), the policy depends
on the lifecycle event:

``on_request``
    Fails closed. The client gets a ``500`` response, the remote endpoint is not called and the remaining rules of the
    event do not run. Rules are often used to deny requests: one that fails must not let them through. The response does
    not tell the client anything about the failure, the log does.

``on_remote_request``, ``on_remote_response``, ``on_response``
    Fail open. The transaction goes on as if the rule had not changed anything, and a ``WARNING`` log names the rule
    level, the script, the endpoint and the error.

Every failure also increments the ``rules_failures_count`` Prometheus counter, labelled by ``endpoint``, ``rule`` (the
lifecycle event) and ``reason`` (``error`` or ``timeout``).

Time budget
:::::::::::

Each script has a time budget, one second by default, set with ``time_budget`` (in seconds) next to the rules:

.. code-block:: toml

    [rules]
    time_budget = 0.5

    [rules."*"."*"]
    on_request = "..."

``time_budget`` is therefore not usable as an endpoint pattern.

Scripts run in worker threads, so a slow script does not make the other transactions wait. When the budget is
exceeded, the proxy stops waiting for the script, ignores what it does afterwards and applies the failure policy
above. **Python cannot stop a running thread**: the script itself keeps running until it ends, holding its thread
(there are eight of them for all rules) and whatever it was doing to the shared objects. Do not write scripts that wait
or loop for long. If all the threads are held by scripts that never end, the following scripts time out in turn.

Reading the response body
:::::::::::::::::::::::::

Responses are streamed: ``response.body`` is not available to ``on_response`` scripts, and reading it raises a
``RuntimeError``. The failure policy applies: the script is logged as failed with a warning naming it, and the
response is sent unchanged. Scripts are synchronous and cannot await ``response.aread()``.
