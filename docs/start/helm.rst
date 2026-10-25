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

The dashboard requires a sign-in. While no administrator exists, HARP prints a setup link in the pod logs at each pod
start (``kubectl logs <pod> | grep "setup#"``); opening it creates the first administrator. Set
``dashboard.public_url`` so that the link names your ingress. See :doc:`/apps/auth/index`. Users declared in
``dashboard.auth`` (deprecated) are rendered into the chart's ConfigMap, which is readable by anyone who can read
ConfigMaps in the namespace: use password hashes (``pbkdf2_sha256``), never plain passwords.


Database
::::::::

The chart has an optional PostgreSQL dependency that can be used to spawn a database for the proxy. You can enable it by
setting ``postgresql.enabled`` to ``true`` in your values, and eventually settings for the related chart.

See `the bitnami/postgresql chart documentation <https://github.com/bitnami/containers/tree/main/bitnami/postgresql>`_.


Values
::::::

.. literalinclude:: ../../misc/helm/charts/harp-proxy/values.yaml
    :language: yaml
