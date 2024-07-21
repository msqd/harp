Patterns and syntax
===================

The rules engine uses rules definition based on 3-levels of pattern matching:

- **endpoint**: the first level allows to filter on which endpoints should match, by endpoint name.
- **request**: the second level allows to filter on the request's fingerprint.
- **stage**: the fird level allows to filter on which stage the filter should apply.

Under those three levels, you'll find a list of python code blocks that will be compiled and executed when the
matching events occurs.

.. include:: examples/rules.rst
