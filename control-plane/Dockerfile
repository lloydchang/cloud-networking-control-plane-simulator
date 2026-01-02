FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    nftables \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pyroute2 \
    pydantic \
    sqlalchemy \
    aiosqlite \
    docker \
    jinja2 \
    prometheus-client \
    psutil \
    grpcio \
    grpcio-tools \
    && mkdir -p /app/data

WORKDIR /app

COPY . /app

# Generate gRPC stubs
RUN python -m grpc_tools.protoc -I./proto --python_out=./api --grpc_python_out=./api ./proto/cloud_networking_control_plane_simulator.proto

EXPOSE 8000 50051

CMD ["python", "-u", "main.py"]
