# Stage 1: Build wheels
FROM python:3.12-alpine AS builder

# Install build dependencies for miniupnpc
RUN apk add --no-cache build-base libffi-dev

WORKDIR /wheels

# Build a wheel for miniupnpc.
RUN pip wheel --no-cache-dir --wheel-dir=/wheels miniupnpc

# Stage 2: Final application image
FROM alpine:latest

# Install Python runtime, PyYAML and libffi
RUN apk add --no-cache python3 py3-yaml libffi

# Copy the miniupnpc wheel from the builder stage
COPY --from=builder /wheels /tmp/wheels

# Install the miniupnpc wheel using pip.
# py3-pip is installed temporarily for this and then removed along with caches to save space.
RUN apk add --no-cache --virtual .pip-build-deps py3-pip \ 
    && pip3 install --no-cache-dir --break-system-packages /tmp/wheels/miniupnpc*.whl \ 
    && apk del .pip-build-deps \ 
    && rm -rf /tmp/wheels /root/.cache/pip /var/cache/apk/*

WORKDIR /app
COPY upnp_client.py /app/upnp_client.py

CMD ["python3", "-u", "upnp_client.py"]
