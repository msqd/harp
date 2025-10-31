Unreleased
==========

Added
-----

- Kitchen-sink demo environment now supports three deployment modes: local (uv run), uvx (from PyPI), and docker (from GHCR)

Changed
-------

- Docker images are now published to both GitHub Container Registry (ghcr.io/msqd/harp) and Docker Hub (makersquad/harp-proxy)
- Version 0.9.x mainline releases also publish to ``makersquad/harp-proxy:latest`` on Docker Hub

Fixed
-----

- Wheel build now includes frontend assets using hatch's force-include configuration
