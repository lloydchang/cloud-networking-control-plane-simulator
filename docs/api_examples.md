# VPC API Examples

This document provides comprehensive API examples for managing VPC resources using the Cloud Networking Control Plane Simulator REST API. These examples use `curl` and mirror the scenarios created in the demo script.

## Base URL

```bash
API_URL="http://localhost:8000"
```

## VPC Management

### Create a VPC

Create a basic VPC with a single CIDR block:

```bash
curl -X POST "${API_URL}/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production VPC",
    "cidr": "10.0.0.0/16",
    "region": "us-east-1"
  }'
```

Create a VPC with secondary CIDR blocks:

```bash
curl -X POST "${API_URL}/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kubernetes Cluster VPC",
    "cidr": "10.1.0.0/16",
    "region": "us-east-1",
    "secondary_cidrs": ["100.64.0.0/16"]
  }'
```

### List All VPCs

```bash
curl -X GET "${API_URL}/vpcs"
```

### Get VPC Details

```bash
VPC_ID="vpc-abc123"
curl -X GET "${API_URL}/vpcs/${VPC_ID}"
```

### Delete a VPC

```bash
VPC_ID="vpc-abc123"
curl -X DELETE "${API_URL}/vpcs/${VPC_ID}"
```

## Subnet Management

### Create a Subnet

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Public Subnet",
    "cidr": "10.0.1.0/24",
    "data_center": "CDC-1"
  }'
```

### List Subnets in a VPC

```bash
VPC_ID="vpc-abc123"
curl -X GET "${API_URL}/vpcs/${VPC_ID}/subnets"
```

## Route Management

### Create an Internet Gateway Route

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "0.0.0.0/0",
    "next_hop": "igw-auto",
    "next_hop_type": "internet_gateway"
  }'
```

### Create a VPN Gateway Route

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "192.168.0.0/16",
    "next_hop": "dc-onprem-001",
    "next_hop_type": "vpn_gateway"
  }'
```

### Create a Cloud Routing Hub Route

```bash
VPC_ID="vpc-abc123"
HUB_ID="hub-xyz789"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "10.0.0.0/8",
    "next_hop": "'${HUB_ID}'",
    "next_hop_type": "cloud_routing_hub"
  }'
```

### Create an Instance Route (NAT)

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "0.0.0.0/0",
    "next_hop": "10.49.96.3",
    "next_hop_type": "instance"
  }'
```

## Internet Gateway

### Attach Internet Gateway to VPC

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/vpcs/${VPC_ID}/internet-gateways"
```

## Cloud Routing Hub Management

### Create a Cloud Routing Hub

```bash
curl -X POST "${API_URL}/hubs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Global Transit Hub",
    "region": "global"
  }'
```

### Add Routes to a Hub

```bash
HUB_ID="hub-xyz789"
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/hubs/${HUB_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "10.1.0.0/16",
    "next_hop": "'${VPC_ID}'",
    "next_hop_type": "cloud_routing_hub"
  }'
```

### Delete a Hub

```bash
HUB_ID="hub-xyz789"
curl -X DELETE "${API_URL}/hubs/${HUB_ID}"
```

## Standalone Data Center Management

### Create a Standalone Data Center

```bash
curl -X POST "${API_URL}/standalone-dcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "On-Premise Data Center",
    "cidr": "192.168.0.0/16",
    "region": "on-prem"
  }'
```

### Create a Subnet in a Standalone DC

```bash
DC_ID="dc-onprem-001"
curl -X POST "${API_URL}/standalone-dcs/${DC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Corporate Network",
    "cidr": "192.168.1.0/24",
    "data_center": "ODC-1"
  }'
```

### Add Routes to a Standalone DC

```bash
DC_ID="dc-onprem-001"
HUB_ID="hub-xyz789"
curl -X POST "${API_URL}/standalone-dcs/${DC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "10.0.0.0/8",
    "next_hop": "'${HUB_ID}'",
    "next_hop_type": "vpn_gateway"
  }'
```

## WireGuard Gateway Management

### Create a WireGuard Gateway

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/wireguard-gateways" \
  -H "Content-Type: application/json" \
  -d '{
    "vpc_id": "'${VPC_ID}'",
    "endpoint": "192.0.2.1:51820",
    "public_key": "US_WEST_PUB_KEY",
    "allowed_ips": "10.10.0.1/32"
  }'
```

## Headscale Node Management

### Create a Headscale Node

```bash
VPC_ID="vpc-abc123"
curl -X POST "${API_URL}/headscale-nodes" \
  -H "Content-Type: application/json" \
  -d '{
    "vpc_id": "'${VPC_ID}'",
    "node_key": "mkey:west-node-01",
    "tailnet": "demo-mesh"
  }'
```

## Scenario Management

### Create a Scenario

```bash
curl -X POST "${API_URL}/scenarios" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Multi-tier Web Application",
    "description": "A three-tier architecture with web, app, and database layers",
    "resource_order": [
      {"type": "vpc", "label": "Production VPC"}
    ]
  }'
```

### List All Scenarios

```bash
curl -X GET "${API_URL}/scenarios"
```

## Complete Example: NAT Router Setup

This example creates a complete NAT router scenario similar to Scenario 28:

```bash
# 1. Create the VPC
VPC_RESPONSE=$(curl -s -X POST "${API_URL}/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NAT Router VPC",
    "cidr": "10.49.96.0/20",
    "region": "us-east-1",
    "scenario": "NAT Router Demo"
  }')

VPC_ID=$(echo $VPC_RESPONSE | jq -r '.id')

# 2. Create subnets for each host
curl -X POST "${API_URL}/vpcs/${VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Host 1 (NAT Router/DNS)",
    "cidr": "10.49.96.3/32",
    "data_center": "CDC-1"
  }'

curl -X POST "${API_URL}/vpcs/${VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Host 2 (FTP Server)",
    "cidr": "10.49.96.4/32",
    "data_center": "CDC-1"
  }'

curl -X POST "${API_URL}/vpcs/${VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Host 3 (Web Server)",
    "cidr": "10.49.96.5/32",
    "data_center": "CDC-1"
  }'

curl -X POST "${API_URL}/vpcs/${VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Host 4 (Windows Server)",
    "cidr": "10.49.96.6/32",
    "data_center": "CDC-1"
  }'

# 3. Configure NAT routing
curl -X POST "${API_URL}/vpcs/${VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "0.0.0.0/0",
    "next_hop": "10.49.96.3",
    "next_hop_type": "instance"
  }'

echo "NAT Router VPC created with ID: ${VPC_ID}"
```

## Complete Example: Managed IPsec VPN

This example creates a managed IPsec VPN scenario similar to Scenario 30:

```bash
# 1. Create the Cloud VPC
CLOUD_VPC=$(curl -s -X POST "${API_URL}/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cloud VPC",
    "cidr": "203.0.113.0/24",
    "region": "us-east-1",
    "scenario": "Managed IPsec"
  }')

CLOUD_VPC_ID=$(echo $CLOUD_VPC | jq -r '.id')

# 2. Create the On-Premises DC
ONPREM_DC=$(curl -s -X POST "${API_URL}/standalone-dcs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "On-Premises Network",
    "cidr": "192.168.1.0/24",
    "region": "on-prem",
    "scenario": "Managed IPsec"
  }')

ONPREM_DC_ID=$(echo $ONPREM_DC | jq -r '.id')

# 3. Create Cloud VPC subnets
curl -X POST "${API_URL}/vpcs/${CLOUD_VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "VPC VPN Gateway",
    "cidr": "203.0.113.2/32",
    "data_center": "CDC-1"
  }'

curl -X POST "${API_URL}/vpcs/${CLOUD_VPC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "App Server (Debian)",
    "cidr": "203.0.113.3/32",
    "data_center": "CDC-1"
  }'

# 4. Create On-Prem DC subnets
curl -X POST "${API_URL}/standalone-dcs/${ONPREM_DC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "On-Prem VPN Gateway",
    "cidr": "192.168.1.1/32",
    "data_center": "ODC-1"
  }'

curl -X POST "${API_URL}/standalone-dcs/${ONPREM_DC_ID}/subnets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Windows Client",
    "cidr": "192.168.1.2/32",
    "data_center": "ODC-1"
  }'

# 5. Configure IPsec tunnel routes
curl -X POST "${API_URL}/vpcs/${CLOUD_VPC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "192.168.1.0/24",
    "next_hop": "'${ONPREM_DC_ID}'",
    "next_hop_type": "vpn_gateway"
  }'

curl -X POST "${API_URL}/standalone-dcs/${ONPREM_DC_ID}/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "203.0.113.0/24",
    "next_hop": "'${CLOUD_VPC_ID}'",
    "next_hop_type": "vpn_gateway"
  }'

echo "Managed IPsec VPN created"
echo "Cloud VPC ID: ${CLOUD_VPC_ID}"
echo "On-Prem DC ID: ${ONPREM_DC_ID}"
```

## Viewing the Network Topology

### Get Complete Network View

```bash
curl -X GET "${API_URL}/vpc"
```

This returns a comprehensive view including all nodes (VPCs, hubs, standalone DCs) and edges (routes, peerings, VPN connections).

## Notes

- All IDs returned by the API should be used in subsequent requests
- The API supports idempotent operations where applicable
- Use `jq` for JSON parsing in shell scripts (as shown in examples)
- Replace placeholder values like `vpc-abc123` with actual IDs from your API responses
