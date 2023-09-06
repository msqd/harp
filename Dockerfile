FROM python:3.11-alpine as build

RUN apk add --no-cache gcc musl-dev libffi-dev

ADD . /sources

RUN (cd /sources; mkdir /wheels; pip wheel --wheel-dir=/wheels .)


FROM node:18-alpine as build-dashboard

RUN npm install -g pnpm
ADD ./frontend /sources/frontend
ADD ./vendors /sources/vendors
RUN (cd /sources/vendors/mkui; pnpm install)
RUN (cd /sources/frontend; pnpm install; pnpm build)


FROM python:3.11-alpine as runtime

COPY --from=build /wheels /usr/local/harp/wheels
COPY --from=build-dashboard /sources/frontend/dist /usr/local/harp/dashboard
RUN pip install --no-index --find-links=/usr/local/harp/wheels harp
COPY --from=build /sources/harp/examples/default.py /etc/harp/entrypoint.py

CMD [ "/usr/local/bin/python", "/etc/harp/entrypoint.py" ]
