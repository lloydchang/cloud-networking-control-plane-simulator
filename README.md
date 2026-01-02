# Cloud Networking Control Plane Simulator

> [!CAUTION]
> **Production Disclaimer**
> This project is a **conceptual simulator**. It is **not** intended for production environments and provides no production-grade guarantees regarding security, performance, or availability.

This project is intended for students, educators, researchers, software engineers, and network engineers. It provides a conceptual exploration of cloud networking internals—demonstrating how VPCs, isolation, and connectivity services are implemented using Linux networking primitives.

## Safety & Security

> [!WARNING]
> **Operational Scope & Security**
> *   **Environment**: Assumes Linux or WSL2. Requires `iproute2`, `nftables`, and `iptables`. `nftables` is the primary mechanism for Security Groups; `iptables` is required for legacy container networking and specific NAT defaults.
> *   **Isolation**: This is a **conceptual simulator**, not a security-hardened environment. Services bound to `127.0.0.1` are accessible locally on the host. Do **not** deploy in a public network or expose ports without explicit host-level firewalling.
> *   **Performance**: Focused on **Control Plane correctness** and **Intent reconciliation**. It does **not** emulate hardware throughput or production-scale traffic. Logical isolation is prioritized over data plane performance.


## Core Concepts

High-level cloud abstractions map to standard Linux networking constructs:

*   **VPCs & Subnets (VRFs with Fallback)**: Uses native Linux **VRFs** for L3 isolation. On hosts without native VRF support (e.g., Docker Desktop on macOS using Apple Silicon, such as M-series), the system automatically falls back to **`iptables`** to maintain logical VPC isolation.
*   **Intent Loop (Fetch-Discover-Diff-Action)**: A centralized **Intent Store** and a four-step **reconciliation loop** (Fetch → Discover → Diff → Action) continuously sync the desired state with the observed fabric. All operations are **idempotent**, ensuring safe retries.
*   **Fabric Overlay**: Uses **BGP EVPN** (simulated via **FRR** within containers) for control-plane route exchange and **VXLAN** for data-plane encapsulation. No actual physical L2/L3 switches are simulated.
*   **Security Groups**: Simulated via **nftables** chains on **Linux namespaces attached to leaf switch interfaces**.
*   **Connectivity Services** (implemented via user-space Linux/container primitives):
    *   **NAT Gateway**: Per-VPC NAT rules implemented via **nftables** for SNAT/DNAT, ensuring per-tenant isolation.
    *   **Internet Gateway**: A **Linux namespace routing traffic** to a virtual public WAN (simulated via NAT and routing).
    *   **Load Balancer**: Layer 4 (TCP) or Layer 7 (HTTP) per-request round-robin balancing via **HAProxy**.

For a deep dive into schemas and sequences, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick Start

### 1. Clone & Prepare

```bash
# Clone the simulator repository
git clone https://github.com/your-repo/cloud-networking-control-plane-simulator.git

# Enter the project directory
cd cloud-networking-control-plane-simulator
```

### 2. Prerequisites
*   Docker Desktop (1 CPU and 1GB RAM would be sufficient to start the containers)
*   Python 3.11+, Make, curl, jq


### 3. Verify Docker Privileges
On systems where Docker requires elevated permissions for network manipulation, ensure your user has appropriate rights or that the Docker daemon is configured to allow `CAP_NET_ADMIN` and `CAP_NET_RAW` capabilities.

### 4. Start Simulator
```bash
make up     # Start all components (Spines, Leaves, Control Plane)
make status # Verify current health of the containerized fabric
make down   # Stop and cleanup all containers and networks
```

> [!NOTE]
> Depending on your Docker configuration, some `make` commands may require `sudo` for proper execution.

> [!NOTE]
> Terminology: In this documentation and codebase, "leaves" denotes the leaf switches in a leaf-spine network topology.

### 5. Provision Sample Environment
```bash
make create-sample-vpc
```
> [!IMPORTANT]
> **Requirements**:
> *   **Docker Compose**: Requires Docker Compose v2+.
> *   **Permissions**: This command requires Docker networking and namespace privileges. On some systems, this may require `sudo` or specific container capabilities (e.g., `CAP_NET_ADMIN`).

This command generates cloud networking control plane demo scenarios:
See [docs/VPC.md](docs/VPC.md)

## API Usage

> [!IMPORTANT]
> **API Access & Security**
> *   **No Authentication**: This simulator implements no authentication. It should **only** be run on `localhost` or within a protected firewall; it should **never** be exposed externally.
> *   **WSL2/Remote**: If using WSL2 or remote hosts, ensure ports 8000 (REST) and 50051 (gRPC) are properly mapped.

### REST API
The control plane exposes a REST API (port 8000) for intent declaration. API operations are **idempotent**, allowing for safe retries without unintended side effects.

Detailed examples for creating **VPCs**, **Subnets**, and **Security Groups** are available in [docs/VPC.md](docs/VPC.md) and [docs/API.md](docs/API.md).

Interactive API documentation is available at

- http://localhost:8000/redoc (ReDoc)
- http://localhost:8000/docs (OpenAPI / Swagger)

once the simulator is running.

### gRPC API
A high-performance gRPC API (port 50051) is provided for management operations and telemetry.

**Quick Check (List VPCs):**
```bash
grpcurl -plaintext localhost:50051 network.NetworkService/ListVPCs
```

For detailed examples including **Creating Resources via gRPC**, streaming telemetry, and the full service definition, see [docs/API.md](docs/API.md#grpc-api).

## Verification & Troubleshooting

### Connectivity Testing
```bash
# Run the automated connectivity test suite
make test-connectivity
```
This script performs a **lightweight smoke test** to validate VPC isolation and internal routing by executing `ping` and `curl` commands between containers:
*   **Success**: Traffic between servers in the same VPC.
*   **Blocked**: Cross-VPC traffic (verifying VRF isolation).

## Visualization & Demos

The simulator includes a rich visualization dashboard and pre-built demonstration scenarios.

*   **Demo Scenarios**: Use the included script to generate complex topologies (Scenarios 0-32):
    ```bash
    python3 control-plane/scripts/create_demo_scenarios.py
    ```
    *This script utilizes the modular `demo_scenarios` package to provision over 30 distinct scenarios, ranging from basic VPCs to complex hybrid and mesh architectures, using generic industry-standard terminology.*

### Observability
Access the observability stack to monitor fabric health:
*   **Grafana** (http://localhost:3333): Dashboards showing container-level metrics (CPU, RAM, simulated traffic) and control-plane state.
*   **Prometheus** (http://localhost:9999): Raw Prometheus metrics (scraped every 10-30s).
*   **VPC View** (http://localhost:8000/vpc): A real-time view of your simulator. See [docs/VPC.md](docs/VPC.md) for details.


**Key Metric**: `reconciliation_duration_ms`
This measures the time taken for a single **reconciliation loop** to sync the **Intent Store** (Desired State) with the actual fabric (Observed State).

> [!NOTE]
> **Scope & Limitations**:
> *   **Aggregation**: Resource metrics (CPU/RAM) and traffic are aggregated per container; VPC counts and reconciliation metrics are scoped to the control plane.
> *   **Simulated Timing**: This metric is simulated and host-dependent. It does **not** reflect actual network latency, packet loss, jitter, or throughput.
> *   **Simulator Range**: Typically 50ms–500ms.
> *   **Production Context**: Real-world systems target sub-second local reconciliation but may have longer global consistency latencies.

### Debugging & Logs
To inspect internal service behavior:
```bash
make logs                   # View all component logs
make logs-control-plane     # View Control Plane API and Reconciler logs
docker compose exec leaf-1 vtysh -c "show ip bgp summary" # Check FRR/BGP status on leaf-1
```

For example:

`docker compose exec leaf-1 vtysh -c "show ip bgp summary"`
```
IPv4 Unicast Summary (VRF default):
BGP router identifier 10.0.0.11, local AS number 65011 vrf-id 0
BGP table version 8
RIB entries 14, using 2688 bytes of memory
Peers 3, using 2151 KiB of memory
Peer groups 1, using 64 bytes of memory

Neighbor          V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
spine-1(10.0.0.1) 4      65000      1126      1128        0    0    0 00:55:59            5        8 N/A
spine-2(10.0.0.2) 4      65000      1126      1128        0    0    0 00:55:59            5        8 N/A
spine-3(10.0.0.3) 4      65000      1126      1128        0    0    0 00:55:59            5        8 N/A

Total number of neighbors 3
```

## Project Structure

```
cloud-networking-control-plane-simulator/
├── control-plane/
│   ├── api/
│   │   ├── rest_api_server.py           # FastAPI REST endpoints
│   │   ├── grpc_api_server.py           # gRPC service implementation
│   │   ├── shared_api_logic.py          # Shared business logic (REST & gRPC)
│   │   └── models.py                    # SQLAlchemy database models
│   ├── reconciler/                      # Intent reconciliation engine
│   ├── scripts/
│   │   ├── create_demo_scenarios.py     # Wrapper for demo scenario generation
│   │   ├── demo_scenarios/              # Modularized demo scenarios package
│   │   │   ├── common.py                # Shared helper functions
│   │   │   ├── basic.py                 # Basic scenarios (0-9)
│   │   │   ├── intermediate.py          # Intermediate scenarios (10-19)
│   │   │   └── advanced.py              # Advanced scenarios (20+)
│   │   └── load_simulation.py           # Performance/load testing script
│   ├── tests/
│   │   ├── test_rest_api.py             # REST API tests
│   │   ├── test_grpc_api.py             # gRPC API tests
│   │   ├── test_shared_api_logic.py     # Core logic tests
│   │   └── test_integration_polyglot.py # REST↔gRPC integration tests
│   └── main.py                          # Entry point
├── services/                            # NAT, firewall, load balancer containers
├── configs/evpn/                        # FRR templates for leaf-spine peering
├── docs/
│   ├── ARCHITECTURE.md                  # System architecture deep-dive
│   ├── API.md                           # REST & gRPC API reference
│   ├── TESTING.md                       # Testing guide & performance findings
│   └── NETWORKING_IMPLEMENTATION.md     # Linux networking details
└── cicd/                                # Canary deployment & rollback automation
```

## Further Reading
*   [Linux VRF Documentation](https://www.kernel.org/doc/Documentation/networking/vrf.txt)
*   [RFC 7432: BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432)
*   [FRR Documentation](https://docs.frrouting.org/)
*   [nftables Wiki](https://wiki.nftables.org/wiki-nftables/index.php/Main_Page)

## License
GNU Affero General Public License v3.0 (AGPL-3.0)

