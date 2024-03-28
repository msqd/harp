################################################################################
# IMAGE: Base build image
#
FROM python:3.12-alpine as base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    BASE="/opt/harp" \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV="/opt/venv" \
    NODE_MAJOR=20

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add gcc musl-dev libffi-dev make \
    && adduser -D harp -G www-data -h ${BASE} -u 500  \
    && mkdir -p ${BASE} \
    && echo 'alias l="ls -lsah --color"' > /opt/harp/.profile \
    && echo 'export PATH="${POETRY_HOME}/bin:${VIRTUAL_ENV}/bin:$PATH"' >> /opt/harp/.profile

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apk,sharing=locked \
    pip install 'poetry==1.7.1' \
    && python3 -m venv ${VIRTUAL_ENV}

RUN chown harp:www-data -R /opt/harp /opt/venv

USER harp
WORKDIR /opt/harp


################################################################################
# IMAGE: Backend builder image (install prod deps in a virtualenv ready to be copied to runtime)
#
FROM base as backend

# Step: Add sources and install dependencies (prod)
USER harp
WORKDIR /opt/harp
ADD --chown=harp:www-data . src

# ... install
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    (cd src; poetry config --list; poetry debug info; poetry install --only main)

# Step: Fix cache directory permissions: this wont delete the content, just the directory that may have strange \
# permissions caused by the cache mounts.
RUN rm -rf .cache


################################################################################
# IMAGE: Development image (ability to use from sources, run tests, run dev servers ...)
#
FROM base as development

# Step: Add system build dependencies
USER root
WORKDIR /root
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    --mount=type=cache,target=/root/.cache,sharing=locked \
    apk add docker \
    && apk add 'nodejs<21' npm \
    && npm install -g pnpm

# Step: Add sources, install dependencies (dev) and build assets
USER harp
WORKDIR /opt/harp
ADD --chown=harp:www-data . src

# ... install and build
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    (cd src; poetry config --list; poetry debug info; poetry install) \
    && (cd src/harp_apps/dashboard/frontend; pnpm install)

# Step: Fix cache directory
RUN rm -rf .cache


################################################################################
# IMAGE: Frontend builder image (ability to compile frontend app into production version)
#
FROM base as frontend

# Step: Add system build dependencies
USER root
WORKDIR /root
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    --mount=type=cache,target=/root/.cache,sharing=locked \
    apk add 'nodejs<21' npm \
    && npm install -g pnpm

USER harp
WORKDIR /opt/harp
ADD --chown=harp:www-data ./harp_apps/dashboard/frontend frontend

RUN (cd frontend; pnpm install; pnpm build)


################################################################################
# IMAGE: Lightest possible image, with only production related abilities
#
FROM python:3.12-alpine as runtime

ENV PYTHONUNBUFFERED=1 \
    BASE="/opt/harp" \
    VIRTUAL_ENV="/opt/venv"

USER root
WORKDIR /root
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add gcc musl-dev libffi-dev make \
    && apk add httpie \
    && adduser -D harp -G www-data -h ${BASE} -u 500  \
    && mkdir -p ${BASE} /var/lib/harp/data \
    && echo 'alias l="ls -lsah --color"' > /opt/harp/.profile \
    && echo 'export PATH="${POETRY_HOME}/bin:${VIRTUAL_ENV}/bin:$PATH"' >> /opt/harp/.profile

RUN chown harp:www-data -R /opt/harp /var/lib/harp/data

USER harp
WORKDIR ${BASE}

COPY --from=backend ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=frontend ${BASE}/frontend/dist ${BASE}/public
COPY --from=backend --chown=harp:www-data ${BASE}/src ${BASE}/src

RUN ln -s /var/lib/harp/data; \
    ln -s /etc/harp.yaml; \
    mkdir bin; \
    ln -s ${BASE}/src/bin/entrypoint bin/entrypoint; \
    mv src/examples ./examples;


ENV DEFAULT__HARP__STORAGE__TYPE="sqlalchemy"
ENV DEFAULT__HARP__STORAGE__URL="sqlite+aiosqlite:///data/harp.db"

EXPOSE 4080

ENTRYPOINT [ "/opt/venv/bin/python", "/opt/harp/bin/entrypoint" ]
