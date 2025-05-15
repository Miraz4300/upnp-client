# Build wheels
FROM python:3.12-alpine AS builder

RUN apk add --no-cache build-base libffi-dev
WORKDIR /wheels
RUN pip wheel --no-cache-dir --wheel-dir=/wheels miniupnpc

# Final Image
FROM alpine:latest

RUN apk add --no-cache python3 py3-yaml libffi
COPY --from=builder /wheels /tmp/wheels
RUN apk add --no-cache --virtual .pip-build-deps py3-pip \ 
    && pip3 install --no-cache-dir --break-system-packages /tmp/wheels/miniupnpc*.whl \ 
    && apk del .pip-build-deps \ 
    && rm -rf /tmp/wheels /root/.cache/pip /var/cache/apk/*

WORKDIR /app
COPY upnp_client.py /app/upnp_client.py

CMD ["python3", "-u", "upnp_client.py"]
