To hash passwords, you can use `python's passlib package <https://passlib.readthedocs.io/en/stable/narr/hash-tutorial.html#hash-tutorial>`_.

.. code:: python

    from passlib.hash import pbkdf2_sha256

    pbkdf2_sha256.hash("password")
