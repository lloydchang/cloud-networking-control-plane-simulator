# Testing & Performance Guide

This document covers the testing infrastructure, coverage achievements, and performance considerations for the Cloud Networking Control Plane Simulator.

## Test Suite Overview

The project uses a multi-layered testing approach:

| Layer | Tool | Purpose |
|-------|------|---------|
| Unit Tests | pytest | Test individual functions and API endpoints |
| Integration Tests | pytest + TestClient | Verify REST↔gRPC interoperability |
| Static Analysis | mypy, flake8 | Type checking and code quality |
| Security Scanning | bandit | Vulnerability detection |
| Load Testing | httpx + asyncio | Performance verification |

## Running Tests

```bash
# Run all tests with coverage
make test-cov

# Run specific test files
cd control-plane && python -m pytest tests/test_rest_api.py -v

# Run linting and formatting
make lint-extreme

# Run security scan
make security-scan
```

## Test Coverage

Current coverage by component:

| Component | Coverage | Notes |
|-----------|----------|-------|
| `models.py` | 100% | All SQLAlchemy models |
| `shared_api_logic.py` | 100% | Core business logic |
| `rest_api_server.py` | 96% | REST API endpoints |
| `grpc_api_server.py` | 94% | gRPC API implementation |

**Uncovered lines**: Database directory creation (startup code) and `serve()` entry points - these are initialization paths typically not exercised in unit tests.

## Test Files

```
control-plane/tests/
├── conftest.py                    # Shared fixtures and DB setup
├── test_shared_api_logic.py       # Core business logic tests
├── test_rest_api.py               # REST API endpoint tests
├── test_grpc_api.py               # gRPC API tests
└── test_integration_polyglot.py   # REST↔gRPC interoperability tests
```

## Performance Findings

### Async/Sync SQLAlchemy Issue

> [!IMPORTANT]
> When using FastAPI with synchronous SQLAlchemy, endpoint functions should use `def`, not `async def`.

**Problem Identified**: During load testing (500 concurrent VPC creations), event loop starvation occurred.

**Root Cause**: 
- FastAPI runs `async def` functions directly on the event loop
- Synchronous SQLAlchemy operations block the event loop
- All other requests are blocked until the DB operation completes

**Solution Applied**:
```python
# ❌ WRONG - Blocks event loop
@app.post("/vpcs")
async def create_vpc(db: Session = Depends(get_db)):
    return db.query(VPCModel).all()  # Blocking call!

# ✅ CORRECT - Runs in threadpool
@app.post("/vpcs")
def create_vpc(db: Session = Depends(get_db)):
    return db.query(VPCModel).all()  # FastAPI runs this in a thread
```

**Result**: The control plane now handles 500+ concurrent requests without blocking.

### Database Concurrency Considerations

For production workloads with high write concurrency, consider:

1. **Async Database Drivers**: Use `databases` or `sqlalchemy[asyncio]` with async drivers
2. **Connection Pooling**: Configure appropriate pool sizes for SQLAlchemy
3. **NoSQL Alternatives**: For very high write throughput, consider:
   - Apache Cassandra
   - ScyllaDB

### Load Testing

The `scripts/load_simulation.py` script provides configurable load testing:

```bash
# Default: 500 VPCs, 50 concurrent
python control-plane/scripts/load_simulation.py

# Custom configuration
NUM_VPCS=1000 CONCURRENCY=100 python control-plane/scripts/load_simulation.py
```

## Writing New Tests

### REST API Tests

```python
from fastapi.testclient import TestClient
from api.rest_api_server import app

client = TestClient(app)

def test_create_vpc():
    response = client.post("/vpcs", json={"name": "test", "cidr": "10.0.0.0/16"})
    assert response.status_code == 201
```

### gRPC Tests

```python
import grpc
from api.grpc_api_server import NetworkService
from api import cloud_networking_control_plane_simulator_pb2

def test_list_vpcs(grpc_stub):
    request = cloud_networking_control_plane_simulator_pb2.ListVPCsRequest(limit=10)
    response = grpc_stub.ListVPCs(request)
    assert response.total >= 0
```

### Integration Tests

Integration tests verify that resources created via one API are visible via the other:

```python
def test_polyglot_flow(grpc_service):
    # Create via REST
    resp = client.post("/vpcs", json={"name": "test", "cidr": "10.0.0.0/16"})
    vpc_id = resp.json()["id"]
    
    # Verify via gRPC
    list_resp = grpc_service.ListVPCs(request, context)
    assert any(v.id == vpc_id for v in list_resp.vpcs)
```

## CI/CD Integration

The Makefile provides targets for CI/CD pipelines:

```makefile
# Full validation pipeline
make all        # lint + test + validate

# Individual steps
make lint       # Basic Python syntax check
make lint-extreme  # mypy + flake8 + black
make test       # Run pytest
make test-cov   # Run pytest with coverage
make security-scan  # Run bandit
```

## Troubleshooting

### "Database is locked" errors

SQLite has limited concurrency. For tests, ensure:
- Each test uses isolated database sessions
- Tests don't run in parallel against the same DB file

### Import errors in tests

Ensure `sys.path` includes the necessary directories:
```python
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))
```

### gRPC stub import issues

The gRPC generated files need the `api/` directory in path:
```python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))
from api import cloud_networking_control_plane_simulator_pb2
```
