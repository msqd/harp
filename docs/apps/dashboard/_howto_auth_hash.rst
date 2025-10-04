To hash passwords, you can use `python's passlib package <https://passlib.readthedocs.io/en/stable/narr/hash-tutorial.html#hash-tutorial>`_.

You can run a Python interpreter with passlib installed using:

.. code:: bash

    uvx --from passlib python

Then use the following code to hash passwords:

.. code:: python

    from passlib.hash import pbkdf2_sha256

    pbkdf2_sha256.hash("password")
