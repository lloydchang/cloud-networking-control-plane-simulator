# Networking Implementation Details

This document clarifies the implementation status of core networking features within the simulator, distinguishing between protocol-level implementation and logical simulator.

## Overview

The Cloud Networking Control Plane Simulator focuses on **Control Plane correctness** and **Intent reconciliation**. To maintain a lightweight and educational environment, certain data plane features are logically modeled when native kernel support is absent, while others are fully implemented in the Linux kernel on-the-fly.

## Implementation Status

| Feature | Control Plane Status | Data Plane / Enforcement |
| :--- | :--- | :--- |
| **EVPN-VXLAN** | **Implemented (FRR)** | **Implemented (Linux Kernel)** |
| **VRFs** | **Simulated** | **Enforced via `iptables` (Logical Fallback)** |
| **VTEPs** | **Implemented (FRR)** | **VXLAN interfaces bound to loopback** |

---

### EVPN-VXLAN & VTEPs

*   **Implementation**: Leaf and spine switches run **FRRouting (FRR)** for control plane signaling. The **Reconciliation Engine** performs actual kernel-level configuration using `ip link` to create and manage VXLAN interfaces (e.g., `vxlan1000`).
*   **VTEP Configuration**: Leaf switches act as VTEPs. The reconciler ensures the loopback and VXLAN interfaces are correctly configured and peered via BGP EVPN, with VXLAN ID (VNI) mapping explicitly controlled by the reconciler logic.
*   **Persistence**: The reconciler uses detailed link discovery (`ip -d link`) to verify VNI and device status. All reconciliation operations are idempotent, ensuring stable and predictable state maintenance.

### VPC Isolation (VRFs)

*   **Implementation**: The reconciler attempts to create native Linux VRF devices. However, some environments (like Docker Desktop on macOS using Apple Silicon, such as M-series) lack the `vrf` kernel module.
*   **Enforcement Fallback**: The simulator automatically falls back to **`iptables`** isolation on the leaf switches when native VRFs are not supported. This provides the required logical VPC isolation (preventing cross-VPC traffic) while maintaining stable control plane behavior.
*   **Unified Discovery**: The reconciler handles "Unified Discovery" by treating both native VRF devices and `iptables` rules equally during state reconciliation to determine if a VPC's isolation is active ("available").

#### Technical Rationale for Fallback
Native VRF support in Linux requires a kernel compiled with `CONFIG_NET_VRF=y`. In this simulator environment:
1.  **Elevated Permissions**: Although the switch containers run in `privileged: true` mode with `NET_ADMIN` capabilities, these only grant permission to *use* existing kernel features; they cannot provide features the kernel doesn't have.
2.  **Host Kernel Constraints**: Containers share the host kernel. On macOS (Docker Desktop on macOS using Apple Silicon, such as M-series), this is a lightweight Linux utility VM.
3.  **Apple Silicon Constraints**: The ARM64 Linux VM used by Docker Desktop on macOS using Apple Silicon, such as M-series on Apple Silicon has a distinct feature set compared to Intel-based environments. Native VRF support remains restricted or uncompiled in the standard Docker utility VM kernel.
4.  **Specific Error**: The error `RTNETLINK answers: Not supported` explicitly confirms that the `vrf` device type is unregistered in the running kernel's driver table.
5.  **Automatic Recovery**: The Reconciliation Engine detects this "Not supported" response and automatically switches to **Logical Isolation** using `iptables`. This ensures VPC boundaries are still enforced despite architecture-specific network limitations.

### Intent-Driven Orchestration

The Reconciliation Engine implements a periodic, "Closed Loop" orchestration cycle triggered by both timers and event changes:
1. **Fetch**: Queries the SQLite database for desired network intent.
2. **Discover**: Inspects leaf switches using `ip link` and `iptables-save` to determine actual state.
3. **Diff**: Computes the difference between intended and actual resource states.
4. **Action**: Executes system commands (`ip link add`, `iptables -A`, etc.) to converge the state.

## Further Reading

*   [Architecture Overview](ARCHITECTURE.md)
*   [Control Plane Design](IDEAS.md)
*   [FRRouting Documentation](https://docs.frrouting.org/)

## Glossary

For a comprehensive list of acronyms and terms used in this documentation (such as EVPN, VTEP, VRF, VNI), please refer to the **[Glossary of Acronyms](ARCHITECTURE.md#glossary-of-acronyms)** in the Architecture Overview.
