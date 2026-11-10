# Pinned by digest, bumped by Dependabot (docker ecosystem). Keep the tag next to the digest.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS builder

# dist/ holds the CI wheel and constraints.txt, the runtime lock exported by `bin/check_docker_lock.py export`:
# the image installs the versions CI tested, not the newest in the wheel's ranges.
COPY dist/*.whl dist/constraints.txt /tmp/wheels/

RUN pip install --no-cache-dir --prefix=/install -c /tmp/wheels/constraints.txt "harp-proxy[argon2,postgresql,sentry] @ file://$(ls /tmp/wheels/*.whl)"


FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app

# zlib1g is fixed in Debian (deb13u1, CVE-2026-76844, CVE-2026-85091) but not yet in the python:3.13-slim base.
# Drop this step once the pinned base ships zlib1g >= 1:1.3.dfsg+really1.3.1-1+deb13u1 (Trivy scan passes without it).
RUN apt-get update \
    && apt-get install --yes --no-install-recommends --only-upgrade zlib1g \
    && rm -rf /var/lib/apt/lists/*

# The runtime image installs nothing: no package manager left behind.
RUN pip uninstall --yes pip setuptools wheel 2>/dev/null; \
    rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.* ; \
    ! python -m pip --version

COPY --from=builder /install /usr/local

# Create non-root user and set up shell aliases
RUN useradd -m -u 1000 harp && \
    chown -R harp:harp /app && \
    echo 'alias l="ls -lsah"' >> /home/harp/.bashrc && \
    echo 'alias cdproject="cd /app"' >> /home/harp/.bashrc && \
    echo 'alias cdharp="cd \$(python -c \"import harp; print(harp.__path__[0])\")"' >> /home/harp/.bashrc && \
    echo 'alias cdapps="cd \$(python -c \"import harp_apps; print(harp_apps.__path__[0])\")"' >> /home/harp/.bashrc

USER harp

EXPOSE 4000-4999

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/healthz', timeout=3)"]

# Note: Use `docker run --init` to enable tini for proper signal handling
ENTRYPOINT ["harp-proxy"]
CMD ["--help"]
