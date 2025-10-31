# Docker Hub Publishing Setup

## Overview

HARP Docker images are published to both:
- **GitHub Container Registry**: `ghcr.io/msqd/harp`
- **Docker Hub**: `makersquad/harp-proxy`

## Required GitHub Secrets

To enable Docker Hub publishing, configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token with push permissions

For details on creating Docker Hub access tokens, see the [official Docker Hub documentation](https://docs.docker.com/security/for-developers/access-tokens/)

## Image Tags

### For Mainline Releases (e.g., 0.9.0)

Published to both registries with multiple tags:

**GHCR:**
- `ghcr.io/msqd/harp:0.9.0`
- `ghcr.io/msqd/harp:0.9`
- `ghcr.io/msqd/harp:0`

**Docker Hub:**
- `makersquad/harp-proxy:0.9.0`
- `makersquad/harp-proxy:0.9`
- `makersquad/harp-proxy:0`
- `makersquad/harp-proxy:latest` ← Only for version 0.9.x releases!

### For Pre-releases (e.g., 0.9.0-rc1)

Published to both registries with exact version only:

**GHCR:**
- `ghcr.io/msqd/harp:0.9.0-rc1`

**Docker Hub:**
- `makersquad/harp-proxy:0.9.0-rc1`

### For Version Branches (e.g., 0.9)

Published to both registries when pushed to version branches:

**GHCR:**
- `ghcr.io/msqd/harp:0.9-git`

**Docker Hub:**
- `makersquad/harp-proxy:0.9-git`

## Testing

Once configured, the workflow will automatically publish to Docker Hub when:
- A version tag is pushed (e.g., `0.9.0`, `0.9.0-rc1`)
- Commits are pushed to a version branch (e.g., `0.9`)

Pull the image from Docker Hub:
```bash
docker pull makersquad/harp-proxy:latest
docker pull makersquad/harp-proxy:0.9.0
docker pull makersquad/harp-proxy:0.9.0-rc1
```

## Troubleshooting

### Authentication Failed

If you see authentication errors:
1. Verify `DOCKERHUB_USERNAME` is correct
2. Regenerate `DOCKERHUB_TOKEN` and update the secret
3. Ensure the token has "Read, Write, Delete" permissions

### Image Not Found

If the image doesn't appear on Docker Hub:
1. Check the GitHub Actions workflow logs
2. Verify the repository exists on Docker Hub: `makersquad/harp-proxy`
3. Ensure the Docker Hub account has access to the repository
