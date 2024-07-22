Rules Engine
============

.. versionadded:: 0.6

Anything can be customized, on a per-request basis, using the rules engine.

Example
:::::::

.. tab-set-code::

    .. code:: toml

        [rules."*"."GET *"]

        on_request = """
        from harp.http import HttpResponse

        if request.headers.get("Authorization") == "I'm root, let me in":
            set_response(HttpResponse("Ok, then."))
        else:
            request.headers["Via"] = "Ferrata"
        """

        on_remote_request = """
        if not request.headers.get("Authorization"):
            request.headers["Authorization"] = "Passphrase I shall pass."
        """

        on_remote_response = """
        response.headers["Cache-Control"] = "max-age=3600"
        """

:doc:`Documentation </apps/rules/index>`
::::::::::::::::::::::::::::::::::::::::

.. include:: /apps/rules/_toc.rst
