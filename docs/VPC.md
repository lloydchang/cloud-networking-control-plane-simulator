# VPC Architecture & Visualization

This document details the VPC implementation, visualization features, and available demo scenarios.

## Visualization Features

The VPC visualization (`/vpc`) provides a real-time logical map of your cloud network.

### Visualization Details

The visualization provides a comprehensive view of your architecture, including:

* **Route Tables**: Per-VPC routing rules.
* **Kubernetes Node Groups**: Visual blocks for simulated container nodes (via `secondary_cidrs`).
* **Cloud Routing Hub**: Centralized hub connections.

### Connection Types

| Type            | Visual Style       | Use Case                                                              |
| :-------------- | :----------------- | :-------------------------------------------------------------------- |
| **Peering**     | Purple Solid Line  | Simple VPC-to-VPC connection in the same region.                      |
| **VPN Gateway** | Orange Dashed Line | Managed encrypted tunnels (e.g., On-Prem to Cloud).                   |
| **Mesh VPN**    | Green Dotted Line  | Zero-trust mesh overlays for secure service-to-service communication. |
| **Routing Hub** | Blue Solid Line    | Centralized routing via Cloud Routing Hub.                            |

## Demo Scenarios

The simulator includes 4 key scenarios, ordered from basic connectivity to complex enterprise architectures. All scenarios use generic, non-proprietary terminology.

### 1. Single VPC

* **Goal**: Simplest cloud network with one public subnet.
* **Architecture**: One VPC containing a single Cloud Data Center (CDC) and a Public Subnet with Internet Gateway access.

### 2. Multi-tier VPC

* **Goal**: Professional VPC with public/private segmentation.
* **Architecture**: A Production VPC with a Public Subnet (internet-accessible) and a Private Subnet for internal application tiers.

### 3. Secure Database Tier

* **Goal**: Isolation of sensitive data between web DMZ and secure backend.
* **Architecture**: A Production Environment VPC with a Web DMZ subnet and a separate Secure DB Tier for database isolation.

### 12. Kubernetes Hybrid

* **Goal**: Cloud Routing Hub and spoke design.
* **Architecture**: Complex enterprise connectivity with secondary addressing.

**VPN Gateway Connections**

| Source | Destination | CIDR |
| :--- | :--- | :--- |
| On-Premise Data Center | Cloud Routing Hub (Non-NAT Flows) | 10.1.0.0/16 |
| On-Premise Data Center | Cloud Routing Hub (Non-NAT Flows) | 10.2.0.0/16 |

**Cloud Routing Hub (NAT Flows)**

| Destination | Target |
| :--- | :--- |
| 0.0.0.0/0 | Shared Services |
| 10.1.0.0/16 | Kubernetes Cluster 1 |
| 10.2.0.0/16 | Kubernetes Cluster 2 |
| 100.64.0.0/16 | Kubernetes Cluster 1 |
| 100.65.0.0/16 | Kubernetes Cluster 2 |

**Cloud Routing Hub (Non-NAT Flows)**

| Destination | Target |
| :--- | :--- |
| 10.1.0.0/16 | Kubernetes Cluster 1 |
| 10.2.0.0/16 | Kubernetes Cluster 2 |
| 10.100.0.0/24 | Shared Services |
| 100.64.0.0/16 | Kubernetes Cluster 1 |
| 100.65.0.0/16 | Kubernetes Cluster 2 |
| 10.0.0.0/16 | dc-10f1f1e8 |

### 13. Multi-Region Hub Transit

* **Goal**: Global connectivity between regional operational centers.
* **Architecture**: Regional Routing Hubs are peered at the hub level to provide high-speed global transit between regional resources.

### 14. Secure Application Service Mesh

* **Goal**: High-level application-layer mesh across multiple tiers.
* **Architecture**: A complex mesh spanning Frontend, Backend, and Data VPCs, demonstrating multi-tier service discovery and security.

### 15. Network Lifecycle: Automated vs Manual

* **Goal**: Contrast automated regional coverage with manual precision.
* **Architecture**: Demonstrates an "Automated Regional" VPC with automatically generated subnets vs a "Manual Controlled" VPC with manually defined subnets.

### 16. Policy Enforcement

* **Goal**: Demonstrate network restriction and security baseline enforcement.
* **Architecture**: A "Restricted VPC" showing how organization-level policies can enforce a secure-by-default environment.

### 17. Hybrid Connectivity: Dedicated & Redundant VPN

* **Goal**: High-speed cloud connectivity with encrypted fallback.
* **Architecture**: Corporate hub connected to a physical Data Center via a high-speed "Dedicated Link" and a VPN tunnel for redundancy.

### 18. Enterprise Hub-and-Spoke

* **Goal**: Large-scale topology with central policy management.
* **Architecture**: Multiple regional spokes connected to a central policy hub for unified security enforcement.

### 19. Virtual Appliance Routing

* **Goal**: Route traffic through a security appliance in a hub VPC.
* **Architecture**: A central hub VPC contains a firewall appliance inspecting traffic between spokes and external resources.

### 20. Hub Gateway Transit

* **Goal**: Spokes use a central hub's VPN gateway.
* **Architecture**: A remote spoke connects to on-premises resources via a central hybrid hub VPN link.

### 21. Data-Scale Network: Secondary CIDR Expansion & Pre-initialized Instances

* **Goal**: High-density networking with secondary CIDR ranges to provide ready-state instance pools (Ready-State Pools).
* **Architecture**: A "High-Density Cluster VPC" using RFC 6598 carrier-grade NAT space (`100.64.0.0/10`) as secondary CIDRs to minimize Compute API rate throttling during massive scale-outs.

### 22. Subnet-Level Peering

* **Goal**: Restrict peering connectivity to specific subnets.
* **Architecture**: Peering between specific "Exposed API" subnets while keeping "Internal Data" subnets isolated.

### 23. Shared Cluster Infrastructure

* **Goal**: Shared VPC for multiple teams with governance.
* **Architecture**: Single enterprise VPC divided into team-specific worker groups with centralized control plane and shared load balancing.

### 24. Cloud-Native Service Hub

* **Goal**: Identity-based service connectivity layer.
* **Architecture**: Global service mesh hub abstracts underlying network complexity, providing logical service-to-service addressing for microservices.

### 25. Hybrid Appliance Bridge

* **Goal**: Managed cloud VPN connecting to a custom software appliance.
* **Architecture**: A "Provider Network" (Managed VPN) connecting to a "Consumer Network" running a custom software gateway appliance.

### 26. AI Infrastructure: Accelerated RDMA Network

* **Goal**: Specialized high-performance networking for AI/ML training workloads.
* **Architecture**: A "AI Training VPC" with RDMA-capable subnets and high-performance accelerator nodes.

### 27. Global Transit: Multi-Region Hubs with GRE Support

* **Goal**: Integration of SASE and SD-WAN using GRE tunneling over global transit hubs.
* **Architecture**: Two regional hubs ("Regional Hub A" and "B") connected via a transit network, with GRE tunnels terminating in a "Security Appliance VPC".

### 28. Dual-Stack Infrastructure: IPv4 & IPv6 Coexistence

* **Goal**: Modern network design supporting concurrent IPv4 and IPv6 traffic flows.
* **Architecture**: A "Dual-Stack VPC" configured with both IPv4 and IPv6 addressing, demonstrating protocol coexistence.

### 29. Cloud Native NAT Router

* **Goal**: Linux-based NAT router managing ingress and egress.
* **Architecture**: A "NAT Router VPC" using a Linux instance to handle NAT and DNS for private hosts, demonstrating custom edge routing.

### 30. Heterogeneous Load Balancing

* **Goal**: Load Balancer distributing traffic across mixed-os backends.
* **Architecture**: A public load balancer distributing requests to a mix of Ubuntu/Nginx, Rocky/Apache, and Debian/Nginx web servers.

### 31. Standard IPsec VPN (Site-to-Site)

* **Goal**: Secure IPsec tunnel between a VPC and on-prem.
* **Architecture**: A "Cloud VPC" connected to an "On-Premises Network" via a standard site-to-site VPN tunnel.

### 32. Remote Access VPN

* **Goal**: Road Warrior connectivity via IKEv2/IPsec.
* **Architecture**: A "Remote Access Hub VPC" accepting connections from remote clients (Road Warriors) via a central VPN gateway.

### 33. Private DNS Discovery

* **Goal**: Internal zone management with private resolution.
* **Architecture**: A "DNS Managed VPC" with a Bind9 server resolving custom internal domains (e.g., `web.example.com`) for private resources.

### 34. Legacy Windows Integration

* **Goal**: Legacy workloads with multiple interfaces.
* **Architecture**: A "Legacy Windows VPC" hosting a multi-interface Windows Server (AD Controller, SQL) with specific public/private segmentation.

## Professional Refinements

* **Server Resource Type**: Distinct aesthetic (solid grey background) for quick identification.
* **Bare IP Formatting**: Server addresses shown as plain IPs to reduce visual clutter.
* **Idempotent Provisioning**: Provisioning scripts perform existing resource checks and optional wiping before scenario generation.

## API Usage

### Create a Kubernetes VPC

```json
POST /vpcs
{
  "name": "k8s-prod",
  "cidr": "10.0.0.0/16",
  "secondary_cidrs": ["100.64.0.0/16"]
}
```

### Create a VPN Gateway

```json
POST /vpn-gateways
{
  "vpc_id": "vpc-xxx",
  "endpoint": "1.2.3.4:51820",
  "public_key": "abc...",
  "allowed_ips": ["10.0.0.0/16"]
}
```
