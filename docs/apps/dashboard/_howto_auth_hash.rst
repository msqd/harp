Accepted algorithms (``dashboard.auth.algorithm``):

- ``pbkdf2_sha256`` (default, recommended): PBKDF2-HMAC-SHA256, nothing to install. It reads the hashes passlib made
  (``$pbkdf2-sha256$...``), so hashes written for earlier versions keep working as they are.
- ``argon2``: Argon2id, needs the extra: ``pip install "harp-proxy[argon2]"``.
- ``plaintext`` (alias ``plain``): **for tests only**. Passwords are stored and compared as written, and HARP logs a
  warning at every start.

Any other value (``bcrypt``, ``md5_crypt``, ...) is refused when the configuration is loaded, with the list above.

To hash a password, run this where HARP is installed, and paste the output as the user's ``password``:

.. code:: bash

    python -c "from getpass import getpass; from harp_apps.dashboard.passwords import hash_password; print(hash_password('pbkdf2_sha256', getpass()))"

Use ``'argon2'`` instead of ``'pbkdf2_sha256'`` for Argon2 hashes.

``users`` can be read from a file with ``users: { fromFile: /path/to/users.yml }``. The path is a trusted setting: HARP
opens whatever file it names, so never build it from untrusted input.
