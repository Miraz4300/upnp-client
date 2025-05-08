FROM python:3.11-slim

RUN pip install miniupnpc pyyaml

COPY upnp_client.py /app/
COPY ports.yaml /app/

WORKDIR /app

CMD ["python", "upnp_client.py"]
