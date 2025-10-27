ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      && rm -rf /var/lib/apt/lists/*

# Copy and install wheel
ARG INSTALL_FROM=local
ARG VERSION

COPY dist/*.whl /tmp/

RUN if [ "$INSTALL_FROM" = "pypi" ]; then \
      echo "Installing from PyPI: harp-proxy==$VERSION"; \
      pip install --no-cache-dir "harp-proxy==$VERSION"; \
    else \
      echo "Installing from local wheel"; \
      pip install --no-cache-dir /tmp/*.whl; \
    fi && \
    rm -rf /tmp/*.whl

# Create non-root user
RUN useradd -m -u 1000 harp && \
    chown -R harp:harp /app

USER harp

EXPOSE 4000-4999

# Note: Use `docker run --init` to enable tini for proper signal handling
ENTRYPOINT ["harp-proxy"]
CMD ["--help"]
