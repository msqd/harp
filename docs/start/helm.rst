Helm & Kubernetes
=================

.. note::

    We use the chart internally to deploy the proxy in our clusters, so it's safe to say that a given version works.
    However, as we go towards general availability, we will most probably make breaking changes to the configuration
    format and to the chart content. Please review the chart content before upgrading.

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

Services are defined for each of the enpoints configured in your values. If you define a ``foobar`` endpoint, you will
get an internal ``foobar-proxy`` service in your cluster, that your applications can use as the proxied endpoint.


Ingress
:::::::

You can enable the dashboard ingress by setting ``ingress.enabled`` to ``true`` in your values. Make sure to add
authentication if your cluster is public!


Database
::::::::

The chart has an optional PostgreSQL dependency that can be used to spawn a database for the proxy. You can enable it by
setting ``postgresql.enabled`` to ``true`` in your values, and eventually settings for the related chart.

See `the bitnami/postgresql chart documentation <https://github.com/bitnami/containers/tree/main/bitnami/postgresql>`_.


Values
::::::

.. literalinclude:: ../../misc/helm/charts/harp-proxy/values.yaml
    :language: yaml
