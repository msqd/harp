Building container images
=========================

To build a local container image, you can run:

.. code-block:: shell

    make buildc

If you run OSX on an ARM64 CPU (M1, M2, M3...), you need to force the build to use the `linux/arm64` platform:

.. code-block:: shell

    make buildc PLATFORM=linux/arm64
