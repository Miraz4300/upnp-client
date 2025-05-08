FROM python:3.13-alpine

RUN pip install miniupnpc pyyaml

COPY upnp_client.py /app/
COPY ports.yaml /app/

WORKDIR /app

CMD ["python", "upnp_client.py"]
