Frequently Asked Questions
==========================

Development related questions
:::::::::::::::::::::::::::::

While building the API reference, `sed` complains about "extra characters at the end of d command" on MacOSX. What's wrong?
---------------------------------------------------------------------------------------------------------------------------

This is a known issue with `sed` on MacOSX, which provides its own `sed` version with different syntax.

You can install GNU `sed` via `brew` and use it instead of the default `sed` shipped with MacOSX.

.. code-block:: shell

    $ brew install gnu-sed

The full error may look like the following:

.. code-block:: shell

    $ make reference
    rm -rf docs/reference/python
    mkdir -p docs/reference/python
    sphinx-apidoc --tocfile index -o docs/reference/python harp
    sed -i "1s/.*/Python Package/" docs/reference/python/index.rst
    sed: 1: "docs/reference/python/i ...": extra characters at the end of d command
    make: *** [reference] Error 1
