#!/bin/bash
set -e

echo "=== Internet Gateway Starting ==="

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Internet Gateway provides:
# 1. Default route to external networks
# 2. Public IP mapping (DNAT/SNAT)
# 3. Routing between VPCs and external

# Add routes for VPC subnets (via fabric network)
ip route add 10.1.0.0/16 via 10.0.0.100 2>/dev/null || true  # Via NAT-GW
ip route add 10.2.0.0/16 via 10.0.0.100 2>/dev/null || true

# Public IP Simulator (Floating IPs)
# Maps public IPs to private instances
# Format: PUBLIC_IP -> PRIVATE_IP

# Example Public IP mappings (configurable via env or API later)
PUBLIC_IPS=${PUBLIC_IPS:-"203.0.113.10:10.1.1.10,203.0.113.11:10.2.1.10"}

echo "Configuring Public IP mappings..."
IFS=',' read -ra MAPPINGS <<< "$PUBLIC_IPS"
for mapping in "${MAPPINGS[@]}"; do
    PUBLIC_IP=$(echo $mapping | cut -d: -f1)
    PRIVATE_IP=$(echo $mapping | cut -d: -f2)
    
    echo "  Mapping $PUBLIC_IP -> $PRIVATE_IP"
    
    # DNAT: Incoming traffic to public IP goes to private IP
    iptables -t nat -A PREROUTING -d $PUBLIC_IP -j DNAT --to-destination $PRIVATE_IP
    
    # SNAT: Outgoing traffic from private IP appears as public IP
    iptables -t nat -A POSTROUTING -s $PRIVATE_IP -j SNAT --to-source $PUBLIC_IP
done

echo "Current routing table:"
ip route

echo "Current NAT rules:"
iptables -t nat -L -n -v

echo "=== Internet Gateway Ready ==="

exec tail -f /dev/null
