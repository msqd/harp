Helm
====

Prerequisite: the docker image must have been pushed for the version (CICD is doing that,
but it takes some time after `git push`).

Update the version number in `misc/helm/charts/harp-proxy/Chart.yaml`. Do not need to be the same as the `appVersion`,
but let's keep the x and y in x.y.z in sync.

.. code:: shell

    vi misc/helm/charts/harp-proxy/Chart.yaml

Package...

.. code:: shell

    helm dependency build misc/helm/charts/harp-proxy
    helm package misc/helm/charts/harp-proxy

Then upload...

.. code:: shell

    helm push harp-proxy-x.y.z.tgz oci://europe-west1-docker.pkg.dev/makersquad/harp
