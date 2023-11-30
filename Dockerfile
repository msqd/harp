# build
FROM python:3.11-alpine as build

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


# build-dev
FROM build as build-dev

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

    #ADD . /sources
#RUN pip install -e .[dev]
#RUN (cd /sources; pip install -e .[dev])


# build dashboard (frontend)
FROM node:18-alpine as build-dashboard

RUN npm install -g pnpm
ADD ./frontend /sources/frontend
ADD ./vendors /sources/vendors
RUN (cd /sources/vendors/mkui; pnpm install)
RUN (cd /sources/frontend; pnpm install; pnpm build)


# runtime
FROM python:3.11-alpine as runtime

#COPY --from=build /wheels /usr/local/harp/wheels
COPY --from=build-dashboard /sources/frontend/dist /usr/local/harp/dashboard
RUN --mount=type=cache,target=/wheels,sharing=locked pip install --no-index --find-links=/wheels harp
COPY --from=build /sources/harp/examples/default.py /etc/harp/entrypoint.py

CMD [ "/usr/local/bin/python", "/etc/harp/entrypoint.py" ]
