Helm & Kubernetes
=================

.. warning::

    The Helm chart is **unsupported** and **not production-ready**. It is not tested against current images and cannot
    start them as is. Do not rely on it. Use :doc:`Docker <docker>` instead.

Install or upgrade
::::::::::::::::::

You can install the published helm chart using the following command:

.. code:: shell

    helm upgrade --install my-proxy oci://europe-west1-docker.pkg.dev/makersquad/harp/harp-proxy

This will install (or upgrade) the latest version of the Harp proxy. If you want to install a specific version, you can
specify it using the ``--version`` flag.

The «my-proxy» string is the name of the release. You can choose any name you want.


Services
::::::::

Services are defined for each of the endpoints configured in your values. If you define a ``foobar`` endpoint, you will
get an internal ``foobar-proxy`` service in your cluster, that your applications can use as the proxied endpoint.


Ingress
:::::::

You can enable the dashboard ingress by setting ``ingress.enabled`` to ``true`` in your values.

The dashboard requires a login. Without ``dashboard.auth`` in ``harp.settings``, HARP generates a password for the
``admin`` user at each pod start and prints it once in the pod logs (``kubectl logs <pod> | grep "Dashboard login"``),
so it changes whenever the pod restarts. To choose your own users, set ``dashboard.auth`` through ``harp.settings``
(see :doc:`/apps/dashboard/index`), taking the password hashes from a secret you manage. ``dashboard.auth.type: none``
serves the dashboard unauthenticated and logs a warning at every start: do not use it with a public ingress.


Database
::::::::

The chart has an optional PostgreSQL dependency that can be used to spawn a database for the proxy. You can enable it by
setting ``postgresql.enabled`` to ``true`` in your values, and eventually settings for the related chart.

See `the bitnami/postgresql chart documentation <https://github.com/bitnami/containers/tree/main/bitnami/postgresql>`_.


Values
::::::

.. literalinclude:: ../../misc/helm/charts/harp-proxy/values.yaml
    :language: yaml
