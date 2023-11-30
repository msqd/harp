################################################################################
# IMAGE: Base build image
#
FROM python:3.11-alpine as base-builder
ENV PATH="/opt/venv/bin:$PATH"

USER root
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add gcc musl-dev libffi-dev \
    && adduser -D harp -G www-data -h /opt/harp -u 500  \
    && mkdir -p /opt/harp /opt/venv \
    && python3.11 -m venv /opt/venv \
    && /opt/venv/bin/pip install -U pip wheel setuptools 'poetry==1.7.1' \
    && echo 'alias l="ls -lsah --color"' > /opt/harp/.profile \
    && echo 'export PATH="/opt/venv/bin:$PATH"' >> /opt/harp/.profile \
    && chown harp:www-data -R /opt/harp /opt/venv



#ADD . /sources
#RUN --mount=type=cache,target=/wheels,sharing=locked (cd /sources; mkdir /wheels; pip wheel --wheel-dir=/wheels .)

FROM base-builder as backend-builder

USER harp
WORKDIR /opt/harp
ADD ./requirements.build.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    pip install -r /tmp/requirements.txt
ADD --chown=harp:www-data . src
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    pip install -e src

################################################################################
# IMAGE: Development image (ability to use from sources, run tests, run dev servers ...
#
FROM base-builder as development

USER root
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    --mount=type=cache,target=/root/.cache,sharing=locked \
    apk add 'nodejs<19' npm \
    && npm install -g pnpm

USER harp
WORKDIR /opt/harp
ADD ./requirements.build-dev.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    pip install -r /tmp/requirements.txt
ADD --chown=harp:www-data . src
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    pip install -e src[dev] \
    && (cd src/vendors/mkui; pnpm install) \
    && (cd src/frontend; pnpm install)



################################################################################
# IMAGE: Frontend builder image (ability to compile frontend app into production version)
#
FROM base-builder as frontend-builder

USER root
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    --mount=type=cache,target=/root/.cache,sharing=locked \
    apk add 'nodejs<19' npm \
    && npm install -g pnpm

USER harp
WORKDIR /sources

ADD --chown=harp:www-data ./frontend frontend
ADD --chown=harp:www-data ./vendors vendors
RUN (cd vendors/mkui; pnpm install)
RUN (cd frontend; pnpm install)
RUN (cd frontend; pnpm build)


################################################################################
# IMAGE: Lightest possible image, with only production related abilities
#
FROM python:3.11-alpine as runtime
ENV PATH="/opt/venv/bin:$PATH"

USER root
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add gcc musl-dev libffi-dev \
    && adduser -D harp -G www-data -h /opt/harp -u 500  \
    && mkdir -p /opt/harp /opt/venv \
    && python3.11 -m venv /opt/venv \
    && /opt/venv/bin/pip install -U pip wheel setuptools 'poetry==1.7.1' \
    && echo 'alias l="ls -lsah --color"' > /opt/harp/.profile \
    && echo 'export PATH="/opt/venv/bin:$PATH"' >> /opt/harp/.profile \
    && chown harp:www-data -R /opt/harp /opt/venv

USER harp
WORKDIR /opt/harp

COPY --from=backend-builder /opt/harp/src/harp/examples/default.py /opt/harp/entrypoint.py

COPY --from=backend-builder /opt/venv /opt/venv
COPY --from=frontend-builder /sources/frontend/dist /opt/harp/public

COPY --from=backend-builder /opt/harp/src /opt/harp/src
RUN --mount=type=cache,target=/opt/harp/.cache,uid=500,sharing=locked \
    pip install -e src

CMD [ "/opt/venv/bin/python", "/opt/harp/entrypoint.py" ]
