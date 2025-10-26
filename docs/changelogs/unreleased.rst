Unreleased
==========

Changed
-------

- Simplified version detection mechanism to use ``importlib.metadata`` for installed packages instead of ``version.txt``
- Version now falls back to ``"unknown"`` instead of ``"0.9-dev"`` when neither git nor package metadata are available

Removed
-------

- Removed ``version.txt`` creation from build process (``bin/sandbox``)
