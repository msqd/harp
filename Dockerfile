################################################################################
# IMAGE: Base build image
#
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    BASE="/opt/harp" \
    VIRTUAL_ENV="/opt/venv" \
    NODE_MAJOR=20 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT="${VIRTUAL_ENV}"

# system dependencies layer
USER root
WORKDIR /root
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
 && apt-get install -y make curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m harp -g www-data -d ${BASE} -u 500 \
 && python3 -m venv ${VIRTUAL_ENV} \
 && chown harp:www-data -R /opt/harp /opt/venv

# Install specific UV version for reproducibility
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

USER harp
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"
RUN echo 'alias l="ls -lsah"' >> ~/.profile \
 && echo 'alias l="ls -lsah"' >> ~/.bashrc

WORKDIR /opt/harp


################################################################################
# IMAGE: Backend builder image (install prod deps in a virtualenv ready to be copied to runtime)
#
FROM base AS backend

# Step: Add system build dependencies
USER root
WORKDIR /root
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Step: Add sources and install dependencies (prod)
USER harp
WORKDIR /opt/harp

# Copy dependency files first for better layer caching
COPY --chown=harp:www-data pyproject.toml uv.lock ./

# Install dependencies in separate layer for better caching
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project

# Copy source code and install project
ADD --chown=harp:www-data . src
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    (cd src; uv sync --frozen)

# Step: Fix cache directory permissions: this wont delete the content (volume), just the directory that may have strange
# permissions caused by the cache mounts.
RUN rm -rf .cache


################################################################################
# IMAGE: Development image (ability to use from sources, run tests, run dev servers ...)
#
FROM base AS development

# Step: Add system build dependencies
USER root
WORKDIR /root
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && curl -sSL https://get.docker.com/ | sh \
    && apt-get install -y build-essential \
    && apt-get install -y nodejs \
    && apt-get install -y vim net-tools iputils-ping netcat-openbsd bind9-host jq \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm

# Step: Add sources, install dependencies (dev) and build assets
USER harp
WORKDIR /opt/harp

# Copy dependency files first for better layer caching
COPY --chown=harp:www-data pyproject.toml uv.lock ./

# Install dependencies in separate layer for better caching
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project

# Copy source code and install project with dev dependencies
ADD --chown=harp:www-data . src
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    (cd src; uv sync --frozen) \
    && (cd src/harp_apps/dashboard/frontend; pnpm install);

# Development image scripts are on the shelf
RUN mv src/bin/development ./bin

# No need for cache directory
RUN rm -rf .cache


################################################################################
# IMAGE: Frontend builder image (ability to compile frontend app into production version)
#
FROM base AS frontend

# Step: Add system build dependencies
USER root
WORKDIR /root

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y build-essential \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm

USER harp
WORKDIR /opt/harp
ADD --chown=harp:www-data ./harp_apps/dashboard/frontend frontend/dashboard

RUN (cd frontend/dashboard; pnpm install; pnpm build)


################################################################################
# IMAGE: Lightest possible image, with only production related abilities
#
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    BASE="/opt/harp" \
    VIRTUAL_ENV="/opt/venv" \
    NODE_MAJOR=20

# system dependencies layer
USER root
WORKDIR /root
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y make curl ca-certificates httpie \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m harp -g www-data -d ${BASE} -u 500  \
    && mkdir -p /var/lib/harp/data

ENV TINI_VERSION="v0.19.0"
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

RUN chown harp:www-data -R /opt/harp /var/lib/harp/data
RUN echo "{}" > /etc/harp.yaml

USER harp
WORKDIR ${BASE}
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"
RUN echo 'alias l="ls -lsah"' >> ~/.profile \
 && echo 'alias l="ls -lsah"' >> ~/.bashrc

COPY --from=backend ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=frontend ${BASE}/frontend/web ${BASE}/src/harp_apps/dashboard/web
COPY --from=backend --chown=harp:www-data ${BASE}/src ${BASE}/src
RUN ln -s ${BASE}/src/harp_apps/dashboard/web public

RUN ln -s /var/lib/harp/data \
    && ln -s /etc/harp.yaml \
    && mv src/bin/runtime ./bin


ENV DEFAULT__HARP__STORAGE__URL="sqlite+aiosqlite:///data/harp.db"

EXPOSE 4080

ENTRYPOINT  [ "/tini", "--", "/opt/venv/bin/harp-proxy" ]
CMD [ "server" ]
