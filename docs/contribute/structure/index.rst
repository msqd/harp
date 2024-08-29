Structure
=========

Applications are simple python packages instrumented with some special artefacts that allows them to be loaded and to
interraact with other components.

The directory structure of an application is the same as any python package, with the following special files (some are
enforced by underlying systems, some are just conventions, and some are optional):

.. toctree::
    :maxdepth: 2

    __app__.py
    __init__.py
    conftest.py
    settings.py
