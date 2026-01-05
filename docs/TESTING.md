# Testing & Performance Guide

This document covers the testing infrastructure, coverage achievements, and performance considerations for the Cloud Networking Control Plane Simulator.

## Test Suite Overview

The project uses a multi-layered testing approach:

| Layer | Tool | Purpose |
|-------|------|---------|
| Unit Tests | pytest | Test individual functions and API endpoints |
| Integration Tests | pytest + TestClient | Verify REST↔gRPC interoperability |
| **Contract Tests** | pytest | Verify global synchronization (Docs ↔ Code ↔ Configs) |
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

Current coverage by component (as of latest commit 5cadd9d):

| Component | Coverage | Status |
|-----------|----------|--------|
| `models.py` | 100% | ✅ All SQLAlchemy models |
| `rest_api_server.py` | 76% | 📈 REST API endpoints |
| `grpc_api_server.py` | 77% | 📈 gRPC API implementation |
| `shared_api_logic.py` | 34% | ⚠️ Shared logic needs more coverage |
| `diagnostic_logger.py` | 27% | ⚠️ Partial coverage |
| **Overall** | **52%** | 📈 **Improved from previous baseline** |

**Recent Improvements** (Commit 596365e):
- ✅ Fixed test environment issues (filesystem permissions)
- ✅ Added missing API functions in shared_api_logic.py
- ✅ Created diagnostic logger tests (25% coverage)
- ✅ Added startup event handler tests
- ✅ Fixed import and environment variable handling

**Uncovered areas**:
- Database initialization and entry points (startup code)
- Some gRPC service methods
- Diagnostic logging methods (partially covered)
- Main.py entry point functions

**Test Files Added**:
```
control-plane/tests/
├── conftest.py                    # Updated with proper test isolation
├── test_diagnostic_logger.py       # NEW: Diagnostic logging tests
├── test_startup.py                # NEW: Startup event handler tests
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
\n## Global Synchronization (Contract) Tests\n\nTo ensure that documentation, configuration, and implementation details remain consistent, we use a suite of **Contract Tests**.\n\n### Purpose\nThese tests act as a guardrail against 'Documentation Drift' and 'Configuration Skew'. They automatically verify that:\n1.  **Topology Consistency**: Switches defined in `topology.json` matches `docker-compose.yml`.\n2.  **Dashboard Accuracy**: The `index.html` static data correctly reflects the underlying topology.\n3.  **Documentation Truth**: Key IP addresses documented in `ARCHITECTURE.md` match the actual configuration in `docker-compose.yml`.\n4.  **Glossary Linkage**: `NETWORKING.md` properly references the central glossary.\n\n### Running Contract Tests\n```bash\npython -m pytest tests/test_global_synchronization.py -v\n```\n\n### Coverage\nThe `tests/test_global_synchronization.py` suite covers:\n- `docker-compose.yml` (Service definitions, Networks)\n- `configs/topology.json` (Switch definitions, VRFs)\n- `docs/ARCHITECTURE.md` (Diagram IPs, Glossary)\n- `docs/index.html` (Static Dashboard Data)
\n## Configuration Validation\n\nThe CI/CD pipeline enforces strict validation rules on the static configuration to prevent misconfigurations from reaching the runtime environment.\n\n### Tooling\nThe `cicd/validate.py` script acts as a static analysis tool for the network configuration. It is invoked via:\n```bash\nmake validate\n# or\nmake deploy  # runs validation before deployment\n```\n\n### Topology Validation (`configs/topology.json`)\nThe `topology.json` file serves as the **Static Blueprint** for the physical fabric. The validation script enforces the following invariants:\n\n1.  **BGP Neighbor Symmetry**: Checks that if Switch A lists Switch B as a neighbor, Switch B also lists Switch A.\n2.  **VNI Uniqueness**: Ensures that `vni` (VXLAN Network Identifier) values are unique per VRF across the fabric.\n3.  **CIDR Overlaps**: Scans for internal logic errors where two subnets might claim overlapping IP ranges.\n4.  **Route Loops**: Basic detection of static route next-hops pointing to themselves or known loops.\n5.  **Security Group Conflicts**: Analyzes rules to prevent conflicting allow/deny statements (warning only).

## Dependency Analysis

The following diagram illustrates the execution dependencies and data flow within the repository.

```text
┌─────────────────┐
│    Makefile     │
└────────┬────────┘
         │
         ├──► make up ────────────────────────────┐
         │     │                                  │
         │     ▼                                  ▼
         │  ┌──────────────────────┐      ┌──────────────────────────┐
         │  │ docker-compose up -d │      │ create_demo_scenarios.py │
         │  └──────────┬───────────┘      └────────────┬─────────────┘
         │             │                               │
         │             ▼                               │
         │    ┌──────────────────┐                     │
         │    │  Control Plane   │◄────────────────────┘
         │    │   (REST API)     │
         │    └──────────┬───────┘
         │               │
         ├──► make       │
         │    validate   │
         │       │       │
         │       ▼       │
         │  ┌────────────┴────────┐
         │  │  cicd/validate.py   │◄────── configs/topology.json
         │  └─────────────────────┘
         │
         ├──► make test ─────────────► pytest (Unit/Contract Tests)
         │
         └──► python generate_site.py ──────────┐
                   │                            │
                   ▼                            ▼
            ┌──────────────┐             ┌──────────────┐
            │ docs/VPC.md  │             │ REST API     │
            │ TESTING.md   │             │ (Live Data)  │
            └──────┬───────┘             └──────┬───────┘
                   │                            │
                   ▼                            ▼
             ┌────────────────────────────────────────┐
             │            docs/index.html             │
             │     (Static Dashboard - Artifact)      │
             └────────────────────────────────────────┘
```
