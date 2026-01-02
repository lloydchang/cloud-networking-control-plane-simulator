FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nftables \
    iproute2 \
    iptables \
    prometheus-node-exporter \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyroute2 docker watchdog

WORKDIR /app
COPY . /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
