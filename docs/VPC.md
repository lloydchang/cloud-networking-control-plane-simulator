# VPC Architecture & Visualization

This document details VPC implementation, visualization features, and available demo scenarios based on the current static data in index.html.

## Visualization Features

The VPC visualization (`/vpc`) provides a real-time logical map of your cloud network.

### Visualization Details

The visualization provides a comprehensive view of your architecture, including:

* **Route Tables**: Per-VPC routing rules.
* **Kubernetes Node Groups**: Visual blocks for simulated container nodes (via `secondary_cidrs`).
* **Cloud Routing Hub**: Centralized hub connections.
* **Standalone Data Centers**: On-premises network integration.
* **VPN Gateways**: Secure tunnel connections.
* **WireGuard Gateways**: Modern VPN connectivity.
* **Headscale Nodes**: Mesh networking capabilities.

### Connection Types

| Type            | Visual Style       | Use Case                                                              |
| :-------------- | :----------------- | :-------------------------------------------------------------------- |
| **Peering**     | Purple Solid Line  | Simple VPC-to-VPC connection in same region.                      |
| **VPN Gateway** | Orange Dashed Line | Managed encrypted tunnels (e.g., On-Prem to Cloud).                   |
| **Mesh VPN**    | Green Dotted Line  | Zero-trust mesh overlays for secure service-to-service communication. |
| **Routing Hub** | Blue Solid Line    | Centralized routing via Cloud Routing Hub.                            |

## Demo Scenarios

The simulator includes 36 key scenarios, ordered from basic connectivity to complex enterprise architectures. All scenarios use generic, non-proprietary terminology.

### 1. Single VPC

* **Goal**: Simplest cloud network with one public subnet.
* **Architecture**: One VPC containing a single Cloud Data Center (CDC) and a Public Subnet with Internet Gateway access.

### 2. Multi-tier VPC

* **Goal**: Professional VPC with public/private segmentation.
* **Architecture**: A Production VPC with a Public Subnet (internet-accessible) and a Private Subnet for internal application tiers.

### 3. Secure Database Tier

* **Goal**: Isolation of sensitive data between web DMZ and secure backend.
* **Architecture**: A Production Environment VPC with a Web DMZ subnet and a separate Secure DB Tier for database isolation.

### 4. Public Load Balancer & Private Backend

* **Goal**: Ingress traffic management with a public listener and private workers.
* **Architecture**: An Application Service VPC with a Frontend Entry subnet containing a Load Balancer and a Backend Pool with application servers.

### 5. NAT Router for Private Subnets

* **Goal**: Controlled internet access for isolated instances.
* **Architecture**: Private subnets route outbound traffic through a centralized NAT Router, preventing direct inbound internet exposure.

### 6. Secure Microservices Mesh

* **Goal**: Secure service-to-service communication.
* **Architecture**: A microservices-oriented network with dedicated subnets for individual services and mesh-based routing.

### 7. Managed VPN

* **Goal**: Secure cloud-to-on-prem or region-to-region connectivity.
* **Architecture**: Encrypted tunnels between distinct environments using generic VPN gateways.

### 8. Private Mesh Overlay

* **Goal**: Zero-trust mesh overlay networking.
* **Architecture**: A coordination server facilitates flat, encrypted mesh connectivity between nodes across arbitrary network boundaries.

### 9. VPC Peering

* **Goal**: Simple VPC-to-VPC connectivity within same region.
* **Architecture**: Two VPCs (Frontend and Backend) connected via bidirectional peering routes, enabling direct communication between resources in different VPCs.

### 10. Private Service Connectivity

* **Goal**: Private service connectivity without full network peering.
* **Architecture**: A "Consumer VPC" connects to a specific "Provider VPC" service via a logical private service endpoint link, maintaining isolation for all other traffic.

### 11. Collaborative Shared Network

* **Goal**: Centralized network management with departmental isolation.
* **Architecture**: A single "Shared Network VPC" divided into isolated subnets for HR, Finance, and IT groups.

### 12. Kubernetes Hybrid Network

* **Goal**: Cloud Routing Hub and spoke design with secondary addressing.
* **Architecture**: Complex enterprise connectivity with Kubernetes clusters, secondary CIDR blocks, and centralized routing through Cloud Routing Hubs.

### 13. Secure Application Service Mesh

* **Goal**: Advanced service mesh with secure communication patterns.
* **Architecture**: Multi-tier service architecture with mesh ingress, service tiers, and storage layers.

### 14. Network Lifecycle: Automated vs Manual

* **Goal**: Demonstrate automated vs manual network management.
* **Architecture**: Comparison between automated subnet provisioning across regions and manual subnet configuration.

### 15. Policy Enforcement

* **Goal**: Network policy compliance and enforcement.
* **Architecture**: Policy-driven network with compliant subnets and security controls.

### 16. Hybrid Connectivity: Dedicated & Redundant VPN

* **Goal**: High-availability hybrid connectivity.
* **Architecture**: Redundant VPN connections between cloud and on-premises environments.

### 17. Enterprise Hub-and-Spoke

* **Goal**: Centralized enterprise network management.
* **Architecture**: Central hub connecting multiple spoke networks (Dev, Billing, Employee Portal, Security Scanner).

### 18. Virtual Appliance Routing

* **Goal**: Integration with virtual network appliances.
* **Architecture**: Network traffic routing through virtual appliances like firewalls.

### 19. Hub Gateway Transit

* **Goal**: Centralized traffic routing through hub gateways.
* **Architecture**: Hub-based transit architecture for traffic management.

### 20. Data-Scale Network: Secondary CIDR Expansion & Pre-initialized Instances

* **Goal**: Large-scale network with expanded addressing.
* **Architecture**: Enterprise-scale network with secondary CIDR blocks and pre-configured instances.

### 21. Subnet-Level Peering

* **Goal**: Granular network connectivity at subnet level.
* **Architecture**: Direct peering between specific subnets across VPCs.

### 22. Shared Cluster Infrastructure

* **Goal**: Multi-tenant cluster sharing.
* **Architecture**: Shared infrastructure with isolated pools for different teams.

### 23. Cloud-Native Service Hub

* **Goal**: Centralized service management hub.
* **Architecture**: Service-oriented architecture with checkout, inventory, and web client components.

### 24. Hybrid Appliance Bridge

* **Goal**: Bridge between cloud and on-prem appliances.
* **Architecture**: Hybrid connectivity with software gateway integration.

### 25. AI Infrastructure: Accelerated RDMA Network

* **Goal**: High-performance AI workloads.
* **Architecture**: GPU cluster with RDMA networking for AI/ML workloads.

### 26. Global Transit: Multi-Region Hubs with GRE Support

* **Goal**: Global multi-region connectivity.
* **Architecture**: Multi-region hub architecture with GRE tunnel support.

### 27. Dual-Stack Infrastructure: IPv4 & IPv6 Coexistence

* **Goal**: IPv4/IPv6 dual-stack networking.
* **Architecture**: Dual-stack network supporting both IPv4 and IPv6 addressing.

### 28. Cloud Native NAT Router

* **Goal**: Software-based NAT routing.
* **Architecture**: Host-based NAT routing with multiple services.

### 29. Heterogeneous Load Balancing

* **Goal**: Multi-platform load balancing.
* **Architecture**: Load balancer supporting heterogeneous server environments.

### 30. Standard IPsec VPN (Site-to-Site)

* **Goal**: Traditional IPsec VPN connectivity.
* **Architecture**: Standard site-to-site IPsec VPN tunnel.

### 31. Remote Access VPN

* **Goal**: Remote user access to private networks.
* **Architecture**: VPN endpoints for remote user connectivity.

### 32. Private DNS Discovery

* **Goal**: Internal DNS resolution and service discovery.
* **Architecture**: Private DNS server with internal service resolution.

### 33. Legacy Windows Integration

* **Goal**: Integration with Windows-based infrastructure.
* **Architecture**: Windows AD and SQL server integration with proper subnet isolation.

### 34. Brownfield Endpoint Adoption

* **Goal**: Integration with existing network infrastructure.
* **Architecture**: Adoption of existing subnets into cloud network management.

### 35. Partial Brownfield Adoption

* **Goal**: Gradual migration of existing networks.
* **Architecture**: Selective adoption of existing network components.

### 36. Brownfield Adoption Under Churn

* **Goal**: Network management during dynamic changes.
* **Architecture**: Handling network topology changes during ongoing operations.

## Scenario Selection

The visualization interface allows you to:
1. **Browse scenarios** using the dropdown menu
2. **Load specific scenarios** to see their network topology
3. **Examine connections** between different network components
4. **Understand relationships** between VPCs, hubs, and standalone data centers

Each scenario demonstrates specific networking concepts and can be used as a reference for designing similar architectures in real cloud environments.

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
