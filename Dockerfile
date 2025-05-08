FROM python:3.13-alpine

# Install build tools temporarily for compiling miniupnpc
RUN apk add --no-cache --virtual .build-deps \
    build-base libffi-dev python3-dev libcap-dev \
 && pip install --no-cache-dir miniupnpc pyyaml pyfiglet \
 && apk del .build-deps  # Remove build tools after install

# Copy only required files
COPY upnp_client.py /app/upnp_client.py
WORKDIR /app

CMD ["python", "-u", "upnp_client.py"]
