# Pinned by digest, bumped by Dependabot (docker ecosystem). Keep the tag next to the digest.
FROM python:3.13-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962 AS builder

COPY dist/*.whl /tmp/wheels/

RUN pip install --no-cache-dir --prefix=/install "harp-proxy[postgresql,mysql] @ file://$(ls /tmp/wheels/*.whl)"


FROM python:3.13-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962

WORKDIR /app

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
