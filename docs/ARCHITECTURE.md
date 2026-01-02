# Architecture Details: Cloud Networking Control Plane Simulator

This document provides a deep dive into the architectural components, data flows, and infrastructure mapping of the cloud networking simulator.

## Core Concepts & Terminology

Before diving into the technical details, it is important to distinguish between the two primary networking layers. This simulator relies on **FRRouting (FRR) containers** for BGP EVPN functionality to achieve full overlay behavior.

*   **Physical Fabric (Fabric)**: The underlying Docker-based network that provides basic reachability between nodes (Spines, Leafs, and Control Plane). This mirrors a physical data center leaf-spine topology.
*   **Logical Overlay (VXLAN-EVPN Overlay Plane)**: The virtualized network built on top of the Fabric using **VXLAN** and **BGP EVPN**. These terms are synonymous in this documentation. This layer provides VPC isolation, Layer-2 extension across leafs, and Layer-3 routing between subnets.
*   **Cloud Routing Hub**: A centralized routing aggregation point that enables transitive routing between multiple VPCs (Hub-and-Spoke). It acts as the "glue" for complex enterprise topologies, facilitating secure east-west traffic inspection and global reachability.

## System Architecture

The following diagram illustrates the logical overlay and its relationship with the Physical Fabric and control plane.

> [!NOTE]
> Diagrams are simplified for clarity. This simulator focuses on **Control Plane correctness** and **Intent reconciliation**. High-throughput data plane behavior is secondary to functional correctness and protocol stability.
>
> **Platform Compatibility**: Native Linux VRFs are used where supported. On platforms without native VRF kernel modules—such as **Apple Silicon (M1-M4) via Docker Desktop**—the simulator automatically falls back to **`iptables`** for logical isolation.

```text
        ┌───────────────────────────────────────────────────────────────┐
        │                       LOGICAL OVERLAY                         │
        │ ┌────────────────┐ ┌────────────────┐ ┌─────────────────────┐ │
        │ │     vpc-100    │ │     vpc-200    │ │      Internet       │ │
        │ │ VNI: 100       │ │ VNI: 200       │ │ CIDR: 203.0.113.0/24│ │
        │ │ VRF: vpc-100   │ │ VRF: vpc-200   │ │ (Simulated WAN)     │ │
        │ │ CIDR: 10.1/16  │ │ CIDR: 10.2/16  │ └──────────┬──────────┘ │
        │ └────────────────┘ └────────────────┘            │            │
        └─────────────────┬────────────────────────────────┼────────────┘
                          │                                │
             ┌────────────┴─────────────┐          ┌───────┴───────┐
             │ VXLAN-EVPN Overlay Plane │          │ Internet-GW   │
             │ - EVPN Type-2: MAC/IP    │          │ (NAT/Router)  │
             │ - EVPN Type-5: L3 routes │          └───────┬───────┘
             │ - Synchronizes VRFs &    │                  │
             │   VNIs across leafs      │          ┌───────┴───────┐
             └────────────┬─────────────┘          │  NAT-Gateway  │
                          │                        │  (SNAT/DNAT)  │
             ┌────────────┴───────────────┐        └───────┬───────┘
             │                            │                │
             ▼                            ▼                │
       ┌───────────┐                ┌───────────┐          │
       │  Spine-1  │◀──────────────▶│  Spine-2  │          │
       │ (Fabric)  │                │ (Fabric)  │          │
       └─────┬─────┘                └─────┬─────┘          │
             │                            │                │
             ▼                            ▼                │
      ┌──────────────┐             ┌──────────────┐        │
      │ Leaf-1       │             │ Leaf-2       │        │
      │ ASN: 65011   │             │ ASN: 65012   │        │
      │ VNI: 100/200 │             │ VNI: 100/200 │        │
      │ VRF: vpc-100 │             │ VRF: vpc-100 │        │
      └─────┬────────┘             └─────┬────────┘        │
            │                            │                 │
            ▼                            ▼                 │
     ┌──────────────┐             ┌──────────────┐         │
     │ Server-1     │             │ Server-2     │         │
     │ (VPC-100)    │             │ (VPC-100)    │         │
     │ 10.1.1.10    │             │ 10.1.2.10    │         │
     └──────────────┘             └──────────────┘         │
            │                                              │
     ┌──────────────┐                                      │
     │ Load-Balancer│ <────────────────────────────────────┘
     │ (VPC-100)    │
     └──────────────┘
```

## Data Flows

### Inbound Traffic Traversal (Internet to VPC)

This diagram shows how a request at `localhost:8080` traverses the simulated layers to reach a VPC server.

```text
[ User ] ──▶ [ Port 8080 ] ──▶ [ Load-Balancer ] ──▶ [ Fabric (VXLAN) ] ──▶ [ Server-1 ]
                │                   │                     │                    │
             Host IP            LB Container        (Decapsulation)         VPC Subnet
          (203.0.113.1)         (10.0.0.100)           (at Leaf)           (10.1.1.10)
```

### Outbound Traffic Traversal (VPC to Internet)

For outbound traffic, the server routes through the Leaf, which performs VTEP encapsulation or local routing, eventually passing through the NAT Gateway.

```text
[ Server-1 ] ──▶ [ Leaf-1 ] ──▶ [ NAT-Gateway ] ──▶ [ Internet-GW ] ──▶ [ Internet ]
      │             │               │                   │                  │
  VPC Subnet     (Encap)        (SNAT Logic)          Public IP          External
 (10.1.1.10)   (VNI 100)      (NAT Container)      (203.0.113.50)        (WAN)
```

## Docker Infrastructure Map

This section maps the architectural concepts above to the physical Docker resources. Note that `Leaf-X` and `Spine-X` are single-instance containers for simulator purposes; high-availability redundancy is not modeled. Additionally, VRF/VNI mapping is logical and depends on the host kernel's capability.

### Container Naming Policy
Standard Docker Compose naming: `[project]-[service]-[replica]`
*   Example: `cloud-networking-control-plane-simulator-control-plane-1`

### Network Mesh Layout
Docker uses **Underscores** for network namespaces and **Hyphens** for container hostnames.

```text
                                NETWORK INFRASTRUCTURE (Docker)
        ┌───────────────────────────────────────────────────────────────────────────────────────────┐
        │                EXTERNAL NETWORK: cloud-networking-control-plane-simulator_internet        │
        │                         (Docker Bridge: 203.0.113.0/24)                                   │
        └───────────────────────────────┬───────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┴───────────────────────────────────────────────────────────┐
        │                FABRIC NETWORK: cloud-networking-control-plane-simulator_fabric            │
        │                         (Docker Bridge: 10.0.0.0/24)                                      │
        └─┬──────────┬────────────┬─────────────┬────────────┬─────────────┬────────────────┬───────┘
          │          │            │             │            │             │                │
    ┌─────┴───┐  ┌───┴────┐  ┌────┴────┐  ┌─────┴────┐  ┌────┴───┐  ┌──────┴──────┐  ┌──────┴───────┐
    │ Spine-X │  │ Leaf-X │  │ Control │  │ Firewall │  │ NAT-GW │  │ Internet-GW │  │ Load-Balancer│
    └─────────┘  └───┬────┘  └─────────┘  └──────────┘  └────────┘  └─────────────┘  └──────────────┘
                     │
          ┌──────────┴─────────────────────┐
          │      VPC ACCESS NETWORKS       │
          ├────────────────────────────────┤
          │ ..._vpc-100-leaf-1             │
          │ ..._vpc-200-leaf-1             │
          └───────────┬──────────────┬─────┘
                      │              │
              ┌───────┴──────┐┌──────┴───────┐
              │   Server-1   ││   Server-4   │
              │   (VPC-100)  ││   (VPC-200)  │
              └──────────────┘└──────────────┘
```

## Control Plane Internals

The Control Plane manages the entire life cycle of the simulated network.

### Reconciliation Lifecycle (Closed Loop)

The Reconciliation Engine implements a periodic, "Closed Loop" orchestration cycle to ensure the system converges on the desired state. This cycle is **idempotent**, meaning it can safely re-run without side effects.

```text
        ┌──────────────┐       ┌──────────────┐
   ────▶│ Intent Store │──────▶│ Diff Engine  │───┐
        │ (Desired)    │       │ (Comparison) │   │
        └──────────────┘       └──────▲───────┘   │
               ▲                      │           ▼
               │               ┌──────┴──────┐  ┌──────────────┐
               │               │ Observation │  │ Enforcement  │
               └───────────────┤ (Heartbeat) │◀─┤ (Healing)    │
                               └─────────────┘  └──────────────┘
```

#### Orchestration Steps
1. **Fetch**: Queries the SQLite `Intent Store` for the desired network state (VPCs, VNIs, Subnets).
2. **Discover**: Inspects the running environment (leaf switches) using `ip link`, `ip addr`, and `iptables-save` to determine the actual state.
3. **Diff**: Computes the specific delta between intended and actual resource states.
4. **Action**: Executes enforcement commands (`ip link add`, `iptables -A`, etc.) to reconcile the differences.

#### Core Principle: Idempotency
All reconciliation operations are designed to be **idempotent**. The system can safely re-run the same "Action" commands multiple times without side effects, ensuring that any transient failures or manual drifts are automatically corrected in the next cycle.

### Component Architecture

```text
                                        ┌──────────────────┐
                                        │   User / CI/CD   │
                                        └─────────┬────────┘
                                                  │ (REST/gRPC)
                                                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          CONTROL PLANE (Python)                           │
│                                                                           │
│  ┌──────────────────┐      ┌──────────────────┐      ┌─────────────────┐  │
│  │   API Server     │──────▶   Intent Store   │──────▶   Reconciler    │  │
│  │ (FastAPI / gRPC) │      │ (SQLite / State) │      │ (Diff Engine)   │  │
│  └──────────────────┘      └──────────────────┘      └────────┬────────┘  │
│                                                               │           │
│           ┌───────────────────────────────────────────────────┼───────────┤
│           │                                                   │           │
│           ▼                                                   ▼           │
│  ┌─────────────────┐                                 ┌─────────────────┐  │
│  │ Netlink Manager │                                 │ Config Generator│  │
│  │ (pyroute2)      │                                 │ (Jinja2)        │  │
│  └────────┬────────┘                                 └────────┬────────┘  │
│           │                                                   │           │
│           │ (Netlink/IP)                                      │ (SSH/ZTP) │
│           ▼                                                   ▼           │
│    ┌──────────────┐                                   ┌───────────────┐   │
│    │ Local Kernel │                                   │ Remote Switch │   │
│    │ (Namespaces) │                                   │ (FRRouting)   │   │
│    └───────┬──────┘                                   └───────┬───────┘   │
└────────────┼──────────────────────────────────────────────────┼───────────┘
             │                                                  │
      [ pyroute2 handles ]                              [ BGP Peering handled ]
      [ local netns/links]                              [ by FRR externally   ]
```

### Logical Isolation vs. Native Enforcement

A key architectural feature is the **Graceful Fallback** for VPC isolation:
*   **Target**: The reconciler attempts to use native Linux `vrf` devices for L3 isolation.
*   **Detection**: If the kernel returns `RTNETLINK answers: Not supported` (common on Apple Silicon hosts), the reconciler detects this missing capability.
*   **Fallback**: The system automatically switches to **`iptables`** based isolation. This ensures that even without native kernel VRFs, VPC boundaries are enforced within the simulator environment.

### Container Dependency
While the Control Plane logic and reconciliation can be tested in isolation, the **FRR containers are required** for full overlay behavior. They handle the BGP EVPN control plane (Type-2 and Type-5 route exchange) that enables cross-leaf communication. Note: While commercial distributions like SONiC often use FRR as their internal control plane, this simulator uses standalone FRR containers for simplicity. No SONiC-specific features or ConfigDB integrations are currently active.

### Codebase Structure

The control plane logic is organized to separate scenario definition from core reconciliation logic.

*   **`control-plane/scripts/create_demo_scenarios.py`**: The main entry point for generating the simulator. It orchestrates the setup and teardown of resources.
*   **`control-plane/scripts/demo_scenarios/`**: A package containing modularized scenario definitions.
    *   `basic.py`: Fundamental scenarios (1-10) like Single VPC, Multi-tier, etc.
    *   `intermediate.py`: More complex setups (11-20) including Hub-and-Spoke and Peering.
    *   `advanced.py`: Enterprise-grade scenarios (21-35) covering Global Transit, Shared VPCs, and Legacy integrations.
*   **`control-plane/api/rest_api_server.py`**: The API Server (`/vpc`) and SQLite Intent Store definitions.
*   **`control-plane/reconciler/reconciler.py`**: Contains the core `ReconciliationEngine` that enforces the desired state on the fabric.

## CI/CD Pipeline Flow

The CI/CD flow ensures that configuration changes are validated before being rolled out to the entire Fabric.

```text
User          Canary Script        Leaf-1 (Canary)      Leaf-2/3 (Prod)
 │                 │                    │                     │
 ├─── make canary ─▶                    │                     │
 │                 ├── 1. Validate ────▶│                     │
 │                 │                    │                     │
 │                 ├── 2. Push Config ─▶│                     │
 │                 │                    │                     │
 │                 ├── 3. Health Chk ──▶│                     │
 │                 │  (sleep 60s...)    │                     │
 │                 │                    │                     │
 │          [Success?] ──────────────────────────┐            │
 │                 │▼                            │            │
 │                 ├── 4. Push Config ───────────────────────▶│ (Rollout)
 │                 │                             │            │
 │           [Failure?] ─────────────────────────┘            │
 │                 │▼                                         │
 │                 ├── 5. Rollback ────▶│                     │
 │                 │                    │                     │
 ◀─── (Exit Code) ─┘                    │                     │
```

### Canary Verification Methods
The `canary.sh` script employs several verification techniques to ensure stability:
*   **Configuration Hash**: Compares the intended configuration state against a hash of the current active configuration on the leaf switch.
*   **Connectivity Probes**: Executes `ping` and `curl` commands from within VPC server namespaces to verify end-to-end reachability.
*   **BGP Session Status**: Queries the FRR API to ensure BGP EVPN peering is "Established" and routes are being exchanged.

## Logging, Telemetry & Observation

As a simulator, observability is crucial for understanding the "closed-loop" behavior.

*   **Metrics**: The Control Plane exposes a Prometheus metric endpoint (`/metrics`). Key signals include `reconciliation_duration_ms`, `active_vpcs_count`, and `drift_detected_total`.
*   **Logging**: All containers output logs to `stdout/stderr`, which are aggregated by Docker. The reconciler provides detailed trace-level logging of every "Discover" and "Action" step.
*   **State Inspection**: The SQLite `Intent Store` can be queried directly to see the "Source of Truth" at any time.

## VPC View

The simulator includes a dedicated visual **VPC View** accessible via `make vpc` or `http://localhost:8000/vpc`.

### Design Philosophy:
The visual **VPC View** ignores the Docker host environment and renders only the resources defined in the Control Plane database (VPCs, Subnets, Gateways, Leaves).

### Persona: The Cloud Networking Architect
The VPC View is designed specifically for the **Cloud Networking Architect** persona. Since the physical infrastructure (Leaves) is static, the Architect needs to see the **Dynamics of Logical Intent**:
*   **VPC Lifecycle**: Visualizing 0, 1, or *N* VPCs as they are created and destroyed.
*   **Logical Mapping**: Real-time visualization of how these logical boundaries map onto the underlying Fabric.
*   **Resource Membership**: Seeing the relationship between Subnets and Gateways within the scope of their parent VPC boundary.

### Resource Model: Logical Boundaries
Aligned with the "VPC as an Isolated Network" principle, the UI uses a **Logical Boundary Model**:
*   **VPC Boundaries**: Rendered as transparent, dashed-border zones. These represent logical network isolation, not "Docker Containers" or physical hardware boxes. 
*   **Membership**: Resources like Subnets, NAT Gateways, and Internet Gateways are visually grouped within these boundaries to show logical ownership.
*   **EVPN Placement**: Blue dashed lines represent the EVPN "placement"—showing which physical Leaf switches are currently hosting the VPC's control plane.

### Source of Truth vs. Configuration
To avoid confusion between static definitions and live state, the simulator distinguishes between three layers:

1.  **Static Blueprint (`configs/topology.json`)**: This is a design-time template. It is used by CI/CD scripts to validate schemas and defines the "golden state" of the underlay and initial VPC requirements.
2.  **Live State API (`/vpc`)**: This is the machine-readable "Source of Truth" from the running Control Plane. It queries the SQLite database in real-time to show what has actually been provisioned.
3.  **VPC View (`/vpc` - HTML)**: The human-readable view that consumes the Live State API. Accessible via `make vpc`.

### Data Flow
1.  **Backend**: The Control Plane exposes a `/vpc` endpoint that exports a curated JSON map of simulator nodes and edges when the `Accept` header is not `text/html`.
2.  **Frontend**: The Dashboard (`/vpc` HTML view) polls this endpoint every 15 seconds.
3.  **Rendering**: Renders a map of the intended and actual network state.

## Performance Caveats

This simulator is designed for functional validation and educational purposes, not for stress-testing or production traffic modeling.
*   **Docker Latency**: Packet traversal through multiple Docker bridges and the userspace-heavy VXLAN implementation will show significantly higher latency than ASIC-based hardware.
*   **Kernel Limitations**: As noted, the lack of `vrf` modules in Docker Desktop on MacOS using Apple Silicon hosts requires fallback to `iptables`, which has different scaling characteristics than native VRFs.
*   **Resource Contention**: Running multiple FRR instances and a Python-based reconciler on a single host may lead to CPU contention during heavy reconciliation cycles. Memory usage scales linearly with the number of VPCs and virtual switches.
*   **MTU Mismatches**: Docker network MTU mismatches (standard 1500 vs. VXLAN overhead) may affect packet fragmentation and throughput if not manually tuned.
*   **Simulated NAT**: NAT/SNAT logic is not hardware-accelerated and runs via Linux kernel `netns` transitions, further limiting throughput.
