Contributor's Guide
===================

This guide will guide you through the journey of either **contributing to HARP**, or **extending it** by writing your
applications. Both topics are covered together because the plugin-based architecture makes it quite similar. This is our
way to create a limit-less system: whatever can be done in the core system can be done in a userland application. And
most of harp core features are actually implemented as applications.

.. note::

    HARP development (either for internals or new applications) **heavily depends on containers**, you should have a
    **working docker environment** first (which is out of the scope of this guide).

Although this guide is mostly written to help you contributing code (or extending the system for your own needs), you
can also **contribute to HARP in many ways that does not involve writing code**: sending feedback, proof-reading
documentation, `opening or contributing to discussions on github <https://github.com/msqd/harp/discussions>`_, reporting
issues, sponsoring the project or suggesting new features (subject to core-team approval), etc.

Don't hesitate to `reach out <https://harp-proxy.net/contact>`_ to us if you want to help but do not know how.

.. table::
    :class: guide-intro
    :widths: 30 70

    +---------------------------------------+-------------------------------------------------------------------------+
    | .. figure:: contributor-guide.jpg     | .. include:: _toc.rst                                                   |
    |    :alt: HARP Proxy Contributor Guide |                                                                         |
    +---------------------------------------+-------------------------------------------------------------------------+
