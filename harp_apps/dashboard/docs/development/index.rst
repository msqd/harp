Dashboard
=========

.. toctree::
   :maxdepth: 2

   tests_unit
   tests_e2e

Recipes
:::::::

How to work on interface without the API?
-----------------------------------------

To work on pure interface development, it is often handy to work using the MSW API mocks instead of the real API.

To do this, you can run the following command:

.. code-block:: bash

    harp start --mock

Caveat: you must use localhost:4080 instead of the ipv6 url.
